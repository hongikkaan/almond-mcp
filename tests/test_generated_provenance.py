from verify_library_sources import verify


def test_generated_asset_manifest_matches_files_and_provenance():
    assert verify() > 0
