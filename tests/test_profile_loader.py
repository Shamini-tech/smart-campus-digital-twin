"""Tests for the profile loader."""
from simulator.profile_loader import load_profiles


def test_profiles_are_renamed_to_campus_ids(tmp_path):
    (tmp_path / "map.csv").write_text(
        "campus_building,bdg2_subtype,building_id,sqm\n"
        "B02,Library,Fox_b,200\n"
        "B01,College Classroom,Fox_a,100\n"
    )
    (tmp_path / "v.csv").write_text(
        "timestamp,Fox_a,Fox_b\n2016-01-01 00:00:00,1,2\n2016-01-01 01:00:00,3,4\n"
    )
    (tmp_path / "s.csv").write_text(
        "timestamp,Fox_a,Fox_b\n2016-01-01 00:00:00,ok,ok\n2016-01-01 01:00:00,ok,imputed\n"
    )
    values, statuses = load_profiles(tmp_path / "v.csv", tmp_path / "s.csv", tmp_path / "map.csv")
    assert list(values.columns) == ["B01", "B02"]
    assert values["B01"].tolist() == [1, 3]
    assert statuses["B02"].iloc[1] == "imputed"