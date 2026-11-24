from __future__ import annotations
import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/"tools"/"blender"/"build_palong_thana_hero.py"
SPEC=importlib.util.spec_from_file_location("build_palong_thana_hero",SCRIPT)
assert SPEC and SPEC.loader
MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)

class PalongThanaHeroTests(unittest.TestCase):
    def fixture(self,root):
        ring=[[90.3486329,23.2186092],[90.348641,23.2187965],[90.348722,23.2187936],[90.348714,23.2186062],[90.3486329,23.2186092]]
        src=root/"source.geojson"; src.write_text(json.dumps({"type":"FeatureCollection","features":[
          {"type":"Feature","properties":{"osm_type":"way","osm_id":601571171001,"source_osm_id":"601571171","name":"Palong Model Thana","name:bn":"পালং মডেল থানা","amenity":"police","building":"yes"},
           "geometry":{"type":"Polygon","coordinates":[ring]}}]}),encoding="utf-8")
        tile=root/"map_manifest.json"; tile.write_text(json.dumps({"tile_id":"tile_23p1835_90p3053","local_origin_lat_lon":[23.2085042,90.3302667]}),encoding="utf-8")
        return src,tile
    def test_exact_osm_feature_and_footprint(self):
        with tempfile.TemporaryDirectory() as d:
            src,tile=self.fixture(Path(d)); g=MOD.read_source(src,tile)
        self.assertEqual(g["source_feature"],"way/601571171001")
        self.assertEqual(g["name_bn"],"পালং মডেল থানা")
        self.assertAlmostEqual(g["area"],173.2,delta=2)
        self.assertEqual(g["ring"][0],g["ring"][-1])
    def test_local_coordinates_follow_map_tile_origin(self):
        x,y=MOD.local_xy(23.21870138,90.34867748,23.2085042,90.3302667)
        self.assertTrue(1800<x<2000); self.assertTrue(1000<y<1200)
    def test_wrong_osm_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            src,tile=self.fixture(Path(d)); data=json.loads(src.read_text()); data["features"][0]["properties"]["source_osm_id"]="999"
            src.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"Expected one source OSM way"):
                MOD.read_source(src,tile)
    def test_cc0_pbr_manifest_and_md5_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); mats={}
            for name in ("weathered_plaster","aged_concrete","exposed_clay_brick"):
                maps={}
                for sem in ("base_color","normal","roughness"):
                    p=root/f"{name}_{sem}.png"; p.write_bytes((name+sem).encode())
                    maps[sem]={"path":str(p),"md5":hashlib.md5(p.read_bytes()).hexdigest()}
                mats[name]={"maps":maps}
            mf=root/"pbr.json"; mf.write_text(json.dumps({"provider":"Poly Haven","asset_license":"CC0-1.0","materials":mats}))
            self.assertEqual(MOD.read_pbr(mf)["license"],"CC0-1.0")
            Path(mats["weathered_plaster"]["maps"]["normal"]["path"]).write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError,"MD5 mismatch"): MOD.read_pbr(mf)

if __name__=="__main__": unittest.main()
