import unittest

from orville_freecad.jobs import step_artifacts, top_level_step_artifact


class JobArtifactTests(unittest.TestCase):
    def test_step_artifacts_filters_step_outputs(self):
        job = {
            "artifacts": [
                {"id": "art_step", "kind": "step", "filename": "part.step"},
                {"id": "art_png", "kind": "png", "filename": "preview.png"},
                {"id": "art_stp", "kind": "other", "filename": "assy.stp"},
            ]
        }

        self.assertEqual([artifact["id"] for artifact in step_artifacts(job)], ["art_step", "art_stp"])

    def test_top_level_step_artifact_prefers_assembly_tree_artifact(self):
        job = {
            "assembly_tree": {"artifact_id": "top_level", "kind": "step"},
            "artifacts": [
                {"id": "child", "kind": "step", "filename": "child.step"},
                {"id": "top_level", "kind": "step", "filename": "assembly.step"},
            ],
        }

        self.assertEqual(top_level_step_artifact(job)["id"], "top_level")

    def test_top_level_step_artifact_uses_tree_metadata_when_artifact_list_omits_it(self):
        job = {
            "assembly_tree": {
                "artifact_id": "top_level",
                "kind": "assembly",
                "label": "assembly",
                "filename": "assembly.step",
            },
            "artifacts": [
                {"id": "child", "kind": "step", "filename": "child.step"},
            ],
        }

        artifact = top_level_step_artifact(job)

        self.assertEqual(artifact["id"], "top_level")
        self.assertEqual(artifact["filename"], "assembly.step")

    def test_top_level_step_artifact_uses_tree_metadata_without_flat_artifacts(self):
        job = {
            "assembly_tree": {
                "artifact_id": "top_level",
                "kind": "step",
                "label": "assembly",
                "filename": "assembly.step",
            },
            "artifacts": [],
        }

        artifact = top_level_step_artifact(job)

        self.assertEqual(artifact["id"], "top_level")
        self.assertEqual(artifact["filename"], "assembly.step")

    def test_top_level_step_artifact_falls_back_to_first_step(self):
        job = {
            "assembly_tree": {},
            "artifacts": [
                {"id": "first", "kind": "step", "filename": "first.step"},
                {"id": "second", "kind": "step", "filename": "second.step"},
            ],
        }

        self.assertEqual(top_level_step_artifact(job)["id"], "first")


if __name__ == "__main__":
    unittest.main()
