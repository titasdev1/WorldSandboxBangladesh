from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from tools.map_pipeline.terrain_elevation import ElevationGrid


class ElevationGridTests(unittest.TestCase):
    def test_bilinear_sampling_returns_local_relative_heights(self):
        heights = np.asarray([
            [100.0, 110.0, 120.0],
            [110.0, 120.0, 130.0],
            [120.0, 130.0, 140.0],
        ])
        grid = ElevationGrid.from_array(
            np.asarray([-10.0, 0.0, 10.0]),
            np.asarray([-10.0, 0.0, 10.0]),
            heights,
        )
        self.assertAlmostEqual(grid.reference_elevation_m, 120.0)
        self.assertAlmostEqual(grid.sample_height(0.0, 0.0), 0.0)
        self.assertAlmostEqual(grid.sample_height(5.0, 5.0), 10.0)
        self.assertAlmostEqual(grid.sample_height(-10.0, -10.0), -20.0)

    def test_sample_coordinates_are_clamped_to_valid_tile_edges(self):
        grid = ElevationGrid.from_array(
            np.asarray([-10.0, 10.0]),
            np.asarray([-10.0, 10.0]),
            np.asarray([[90.0, 100.0], [110.0, 120.0]]),
        )
        self.assertAlmostEqual(grid.sample_height(-100.0, -100.0), grid.sample_height(-10.0, -10.0))
        self.assertAlmostEqual(grid.sample_height(100.0, 100.0), grid.sample_height(10.0, 10.0))

    def test_terrain_mesh_contains_relief_and_upward_faces(self):
        grid = ElevationGrid.from_array(
            np.asarray([-20.0, 0.0, 20.0]),
            np.asarray([-20.0, 0.0, 20.0]),
            np.asarray([
                [10.0, 12.0, 14.0],
                [12.0, 14.0, 16.0],
                [14.0, 16.0, 18.0],
            ]),
        )
        mesh = grid.make_mesh()
        self.assertEqual(len(mesh.vertices), 9)
        self.assertEqual(len(mesh.faces), 8)
        self.assertGreater(float(mesh.bounds[1][2] - mesh.bounds[0][2]), 1.0)
        self.assertTrue(np.all(mesh.face_normals[:, 2] > 0.0))

    def test_drape_mesh_follows_slope_and_preserves_object_offset(self):
        grid = ElevationGrid.from_array(
            np.asarray([-10.0, 10.0]),
            np.asarray([-10.0, 10.0]),
            np.asarray([[100.0, 110.0], [110.0, 120.0]]),
        )
        mesh = trimesh.creation.box(extents=(10.0, 10.0, 2.0))
        before = mesh.vertices.copy()
        grid.drape_mesh(mesh, offset_m=0.35)
        self.assertTrue(np.all(mesh.vertices[:, 2] >= before[:, 2] - 10.0))
        self.assertGreater(float(mesh.vertices[:, 2].max() - mesh.vertices[:, 2].min()), 2.0)
        self.assertAlmostEqual(
            float(mesh.vertices[:, 2].max() - mesh.vertices[:, 2].min()),
            float(before[:, 2].max() - before[:, 2].min()) + 10.0,
        )

    def test_manifest_records_grid_and_elevation_range(self):
        grid = ElevationGrid.from_array(
            np.asarray([-1.0, 1.0]),
            np.asarray([-1.0, 1.0]),
            np.asarray([[50.0, 60.0], [70.0, 80.0]]),
            source_path="fixture-dem.tif",
        )
        manifest = grid.to_manifest(spacing_m=1.0)
        self.assertEqual(manifest["status"], "DEM_BACKED")
        self.assertEqual(manifest["source_file"], "fixture-dem.tif")
        self.assertEqual(manifest["grid_samples"], 4)
        self.assertGreater(manifest["relative_max_elevation_m"], manifest["relative_min_elevation_m"])

    def test_geotiff_sampling_builds_metric_heightfield(self):
        import rasterio
        from rasterio.transform import from_origin

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture_dem.tif"
            data = np.fromfunction(
                lambda row, column: 100.0 + row * 2.0 + column * 3.0,
                (20, 20),
                dtype=np.float32,
            ).astype(np.float32)
            profile = {
                "driver": "GTiff",
                "height": data.shape[0],
                "width": data.shape[1],
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:4326",
                "transform": from_origin(0.0, 0.01, 0.0005, 0.0005),
                "nodata": -9999.0,
            }
            with rasterio.open(path, "w", **profile) as dataset:
                dataset.write(data, 1)

            grid = ElevationGrid.from_geotiff(
                path,
                bbox_south_west_north_east=(0.0015, 0.0015, 0.0085, 0.0085),
                origin_lat=0.005,
                origin_lon=0.005,
                width_m=778.0,
                depth_m=778.0,
                spacing_m=100.0,
            )
            self.assertEqual(grid.source_crs, "EPSG:4326")
            self.assertGreater(grid.sample_count, 20)
            self.assertGreater(
                float(np.max(grid.elevations_m) - np.min(grid.elevations_m)),
                10.0,
            )
            self.assertEqual(grid.make_mesh().vertices.shape[1], 3)

    def test_geotiff_rejects_tiles_with_nodata_holes(self):
        import rasterio
        from rasterio.transform import from_origin

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture_nodata.tif"
            data = np.full((20, 20), 25.0, dtype=np.float32)
            data[10, 10] = -9999.0
            profile = {
                "driver": "GTiff",
                "height": data.shape[0],
                "width": data.shape[1],
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:4326",
                "transform": from_origin(0.0, 0.01, 0.0005, 0.0005),
                "nodata": -9999.0,
            }
            with rasterio.open(path, "w", **profile) as dataset:
                dataset.write(data, 1)
            with self.assertRaisesRegex(ValueError, "NoData"):
                ElevationGrid.from_geotiff(
                    path,
                    bbox_south_west_north_east=(0.0015, 0.0015, 0.0085, 0.0085),
                    origin_lat=0.005,
                    origin_lon=0.005,
                    width_m=778.0,
                    depth_m=778.0,
                    spacing_m=100.0,
                )

    def test_geotiff_rejects_unreasonably_dense_mesh(self):
        import rasterio
        from rasterio.transform import from_origin

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture_dem.tif"
            data = np.full((20, 20), 25.0, dtype=np.float32)
            profile = {
                "driver": "GTiff",
                "height": data.shape[0],
                "width": data.shape[1],
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:4326",
                "transform": from_origin(0.0, 0.01, 0.0005, 0.0005),
                "nodata": -9999.0,
            }
            with rasterio.open(path, "w", **profile) as dataset:
                dataset.write(data, 1)
            with self.assertRaisesRegex(ValueError, "samples"):
                ElevationGrid.from_geotiff(
                    path,
                    bbox_south_west_north_east=(0.0015, 0.0015, 0.0085, 0.0085),
                    origin_lat=0.005,
                    origin_lon=0.005,
                    width_m=778.0,
                    depth_m=778.0,
                    spacing_m=1.0,
                    max_samples=100,
                )


if __name__ == "__main__":
    unittest.main()
