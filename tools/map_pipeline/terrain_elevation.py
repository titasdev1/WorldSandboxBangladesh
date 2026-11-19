"""DEM-backed terrain sampling and mesh generation for A-Square map tiles.

The game does not download a proprietary map viewer's tiles. This module reads a
locally supplied, licensed GeoTIFF elevation raster and creates a deterministic
heightfield in the same local metric coordinates as the OSM/Overture geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


EARTH_RADIUS_M = 6_378_137.0


@dataclass
class ElevationGrid:
    """Regular east/north elevation grid, with heights relative to a local datum."""

    x_values: np.ndarray
    y_values: np.ndarray
    elevations_m: np.ndarray
    reference_elevation_m: float
    source_path: str
    source_crs: str
    source_nodata: float | None
    sample_count: int

    @classmethod
    def from_geotiff(
        cls,
        path: str | Path,
        *,
        bbox_south_west_north_east: tuple[float, float, float, float],
        origin_lat: float,
        origin_lon: float,
        width_m: float,
        depth_m: float,
        spacing_m: float = 30.0,
        max_samples: int = 500_000,
    ) -> "ElevationGrid":
        """Read a licensed DEM and sample it onto a bounded local metric grid.

        Reprojection is handled by Rasterio from EPSG:4326 into the raster CRS.
        Any NoData in the requested grid is a hard error: silently filling holes
        with invented zero-height terrain would be worse than rejecting the tile.
        """
        dem_path = Path(path)
        if not dem_path.is_file():
            raise FileNotFoundError(f"DEM GeoTIFF does not exist: {dem_path}")
        if spacing_m <= 0.0 or width_m <= 0.0 or depth_m <= 0.0:
            raise ValueError("DEM spacing and tile dimensions must be positive")

        try:
            import rasterio
            from rasterio.warp import transform as transform_coordinates
        except ImportError as exc:  # pragma: no cover - environment-specific guard
            raise RuntimeError("Rasterio is required to read GeoTIFF DEM sources") from exc

        south, west, north, east = bbox_south_west_north_east
        if not (-90 < south < north < 90 and -180 < west < east < 180):
            raise ValueError("DEM bounds must be valid south, west, north, east coordinates")

        columns = max(2, int(np.ceil(width_m / spacing_m)) + 1)
        rows = max(2, int(np.ceil(depth_m / spacing_m)) + 1)
        sample_count = rows * columns
        if sample_count > max_samples:
            raise ValueError(
                f"DEM grid would contain {sample_count:,} samples (limit {max_samples:,}); "
                "increase spacing_m or use smaller map tiles"
            )

        x_values = np.linspace(-width_m * 0.5, width_m * 0.5, columns, dtype=np.float64)
        y_values = np.linspace(-depth_m * 0.5, depth_m * 0.5, rows, dtype=np.float64)
        local_x, local_y = np.meshgrid(x_values, y_values)

        latitudes = origin_lat + np.degrees(local_y / EARTH_RADIUS_M)
        longitude_scale = EARTH_RADIUS_M * np.cos(np.radians(origin_lat))
        if abs(longitude_scale) < 1e-6:
            raise ValueError("Local equirectangular projection is unstable at this latitude")
        longitudes = origin_lon + np.degrees(local_x / longitude_scale)

        with rasterio.open(dem_path) as dataset:
            if dataset.count < 1:
                raise ValueError("DEM raster has no data bands")
            if dataset.crs is None:
                raise ValueError("DEM raster has no CRS; georeferenced elevation is required")
            if dataset.width < 2 or dataset.height < 2:
                raise ValueError("DEM raster is too small to sample a terrain surface")

            flat_lon = longitudes.ravel().tolist()
            flat_lat = latitudes.ravel().tolist()
            projected_x, projected_y = transform_coordinates(
                "EPSG:4326", dataset.crs, flat_lon, flat_lat
            )
            samples = dataset.sample(zip(projected_x, projected_y), indexes=1, masked=True)
            raw_values: list[float] = []
            invalid_indices: list[int] = []
            band_scale = float(dataset.scales[0]) if dataset.scales else 1.0
            band_offset = float(dataset.offsets[0]) if dataset.offsets else 0.0
            nodata = dataset.nodata
            for index, sample in enumerate(samples):
                value = sample[0]
                if np.ma.is_masked(value):
                    invalid_indices.append(index)
                    raw_values.append(float("nan"))
                    continue
                numeric = float(value) * band_scale + band_offset
                if not np.isfinite(numeric) or (nodata is not None and float(value) == float(nodata)):
                    invalid_indices.append(index)
                    raw_values.append(float("nan"))
                    continue
                raw_values.append(numeric)

            if invalid_indices:
                raise ValueError(
                    f"DEM does not cover the complete requested tile: "
                    f"{len(invalid_indices):,}/{sample_count:,} samples are NoData/outside raster"
                )

            absolute_heights = np.asarray(raw_values, dtype=np.float64).reshape(rows, columns)
            reference_height = float(np.median(absolute_heights))
            relative_heights = absolute_heights - reference_height
            source_crs = dataset.crs.to_string()

        if not np.isfinite(relative_heights).all():
            raise ValueError("DEM produced non-finite elevation samples")
        return cls(
            x_values=x_values,
            y_values=y_values,
            elevations_m=relative_heights,
            reference_elevation_m=reference_height,
            source_path=dem_path.name,
            source_crs=source_crs,
            source_nodata=None if nodata is None else float(nodata),
            sample_count=sample_count,
        )

    @classmethod
    def from_array(
        cls,
        x_values: np.ndarray,
        y_values: np.ndarray,
        absolute_elevations_m: np.ndarray,
        *,
        source_path: str = "synthetic-test-dem",
    ) -> "ElevationGrid":
        """Build a deterministic grid for unit tests and offline fixture scenes."""
        x_axis = np.asarray(x_values, dtype=np.float64)
        y_axis = np.asarray(y_values, dtype=np.float64)
        heights = np.asarray(absolute_elevations_m, dtype=np.float64)
        if x_axis.ndim != 1 or y_axis.ndim != 1 or len(x_axis) < 2 or len(y_axis) < 2:
            raise ValueError("Elevation axes must be one-dimensional and contain at least two samples")
        if heights.shape != (len(y_axis), len(x_axis)):
            raise ValueError("Elevation array shape must be (len(y_values), len(x_values))")
        if not np.all(np.diff(x_axis) > 0) or not np.all(np.diff(y_axis) > 0):
            raise ValueError("Elevation axes must be strictly increasing")
        if not np.isfinite(heights).all():
            raise ValueError("Elevation samples must all be finite")
        reference = float(np.median(heights))
        return cls(
            x_values=x_axis,
            y_values=y_axis,
            elevations_m=heights - reference,
            reference_elevation_m=reference,
            source_path=source_path,
            source_crs="synthetic",
            source_nodata=None,
            sample_count=int(heights.size),
        )

    def sample_height(self, x: float, y: float) -> float:
        """Bilinearly interpolate relative ground height at local east/north metres."""
        x_clamped = float(np.clip(x, self.x_values[0], self.x_values[-1]))
        y_clamped = float(np.clip(y, self.y_values[0], self.y_values[-1]))
        ix = int(np.clip(np.searchsorted(self.x_values, x_clamped, side="right") - 1, 0, len(self.x_values) - 2))
        iy = int(np.clip(np.searchsorted(self.y_values, y_clamped, side="right") - 1, 0, len(self.y_values) - 2))
        x0, x1 = float(self.x_values[ix]), float(self.x_values[ix + 1])
        y0, y1 = float(self.y_values[iy]), float(self.y_values[iy + 1])
        tx = 0.0 if x1 == x0 else (x_clamped - x0) / (x1 - x0)
        ty = 0.0 if y1 == y0 else (y_clamped - y0) / (y1 - y0)
        h00 = float(self.elevations_m[iy, ix])
        h10 = float(self.elevations_m[iy, ix + 1])
        h01 = float(self.elevations_m[iy + 1, ix])
        h11 = float(self.elevations_m[iy + 1, ix + 1])
        lower = h00 * (1.0 - tx) + h10 * tx
        upper = h01 * (1.0 - tx) + h11 * tx
        return lower * (1.0 - ty) + upper * ty

    def drape_mesh(self, mesh: trimesh.Trimesh, *, offset_m: float = 0.0) -> trimesh.Trimesh:
        """Conform an existing z-up mesh to the DEM while retaining its local relief."""
        if len(mesh.vertices) == 0:
            return mesh
        vertices = np.asarray(mesh.vertices, dtype=np.float64).copy()
        heights = np.fromiter(
            (self.sample_height(float(x), float(y)) for x, y in vertices[:, :2]),
            dtype=np.float64,
            count=len(vertices),
        )
        vertices[:, 2] += heights + float(offset_m)
        mesh.vertices = vertices
        return mesh

    def make_mesh(self) -> trimesh.Trimesh:
        """Create a triangulated Z-up ground mesh from the sampled elevation grid."""
        rows, columns = self.elevations_m.shape
        xx, yy = np.meshgrid(self.x_values, self.y_values)
        vertices = np.column_stack((xx.ravel(), yy.ravel(), self.elevations_m.ravel()))
        indices = np.arange(rows * columns, dtype=np.int64).reshape(rows, columns)
        top_left = indices[:-1, :-1].ravel()
        top_right = indices[:-1, 1:].ravel()
        bottom_left = indices[1:, :-1].ravel()
        bottom_right = indices[1:, 1:].ravel()
        faces = np.vstack((
            np.column_stack((top_left, top_right, bottom_right)),
            np.column_stack((top_left, bottom_right, bottom_left)),
        ))
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        mesh.metadata["terrain_source"] = self.source_path
        mesh.metadata["terrain_reference_elevation_m"] = self.reference_elevation_m
        mesh.metadata["terrain_grid_samples"] = self.sample_count
        try:
            mesh.fix_normals()
        except Exception:
            pass
        return mesh

    def to_manifest(self, *, spacing_m: float) -> dict[str, Any]:
        return {
            "status": "DEM_BACKED",
            "source_file": self.source_path,
            "source_crs": self.source_crs,
            "reference_elevation_m": round(self.reference_elevation_m, 3),
            "relative_min_elevation_m": round(float(np.min(self.elevations_m)), 3),
            "relative_max_elevation_m": round(float(np.max(self.elevations_m)), 3),
            "grid_columns": int(len(self.x_values)),
            "grid_rows": int(len(self.y_values)),
            "grid_samples": int(self.sample_count),
            "nominal_spacing_m": round(float(spacing_m), 3),
        }
