import os
import tempfile
import unittest
from unittest import mock

from jobhunt import generator, providers, scraper, settings, server


class Fake:
    def complete(self, system, prompt):
        return "TAILORED CV\n" + generator.MARK + "\nNEW LETTER"


JOB = {"title": "Python Developer", "company": "Acme", "location": "Remote", "work_mode": "remote",
       "url": "http://x/y", "description": "python django sql"}


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.environ["JOBHUNT_HOME"] = self.d

    def test_settings_hide_keys(self):
        settings.save({"provider": "claude", "api_keys": {"claude": "sk-secret"}})
        pub = settings.public(settings.load())
        self.assertEqual(pub["keys_set"], ["claude"])
        self.assertNotIn("sk-secret", str(pub))

    def test_provider_needs_key(self):
        with self.assertRaises(RuntimeError):
            providers.get_provider({"provider": "openai", "api_keys": {}})

    def test_auto_picks_local(self):
        with mock.patch.object(providers, "detect_local", return_value=[{"name": "ollama", "label": "", "models": ["llama3"]}]):
            p = providers.get_provider({"provider": "auto", "api_keys": {}})
        self.assertEqual((p.name, p.model), ("ollama", "llama3"))

    def test_match_and_filter(self):
        cv = scraper.tokens("python django developer sql")
        other = dict(JOB, title="Chef", description="cooking")
        self.assertGreater(scraper.score(cv, JOB), scraper.score(cv, other))
        self.assertEqual(scraper.filter_jobs([JOB], "Paris", "remote"), [JOB])
        self.assertEqual(scraper.filter_jobs([JOB], "Paris", "in-person"), [])

    def test_find_jobs(self):
        jobs = scraper.find_jobs("python python django", "", "remote", sources=[lambda q: [dict(JOB)]])
        self.assertEqual(len(jobs), 1)

    def test_tailor_and_auto_apply(self):
        self.assertEqual(generator.tailor(Fake(), "cv", "cl", JOB), {"cv": "TAILORED CV", "cover_letter": "NEW LETTER"})
        with mock.patch.object(providers, "get_provider", return_value=Fake()):
            r = server.run_generate({"job": JOB, "cv": "cv", "cover_letter": "cl", "auto_apply": True})
        self.assertTrue(os.path.exists(r["saved_to"]))


if __name__ == "__main__":
    unittest.main()
