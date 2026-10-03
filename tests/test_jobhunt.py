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

    def test_country_search_ireland(self):
        self.assertEqual(scraper.resolve_country("Ireland"), "ireland")
        self.assertEqual(scraper.resolve_country("Dublin"), "ireland")
        seen = []

        def ms(q, country=None):
            seen.append(country)
            return [{**JOB, "url": "m", "company": "Microsoft", "location": "Dublin, Ireland", "work_mode": "in-person"},
                    {**JOB, "url": "n", "location": "Seattle, United States", "work_mode": "in-person"}]
        ms.country_aware = True
        jobs = scraper.find_jobs("python django", "Ireland", "in-person", sources=[ms])
        self.assertEqual([j["company"] for j in jobs], ["Microsoft"])
        self.assertEqual(set(seen), {"ireland"})

    def test_company_sources_registered(self):
        names = {s.__name__ for s in scraper.SOURCES}
        self.assertTrue({"search_microsoft", "search_google", "search_greenhouse"} <= names)

    def test_microsoft_parsing(self):
        resp = {"operationResult": {"result": {"jobs": [{"title": "SWE", "jobId": "1", "properties": {
            "locations": ["Dublin, Ireland"], "description": "<b>python</b>"}}]}}}
        with mock.patch.object(scraper, "_request", return_value=resp) as r:
            jobs = scraper.search_microsoft("python", "ireland")
        self.assertIn("lc=Ireland", r.call_args[0][0])
        self.assertEqual(jobs[0]["company"], "Microsoft")

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


class PdfAndTrackerTests(unittest.TestCase):
    def test_pdf_roundtrip(self):
        from jobhunt import pdf
        text = "Jane Doe (Engineer)\nPython \\ Go\n" + "\n".join(f"line {i}" for i in range(120))
        out = pdf.pdf_to_text(pdf.text_to_pdf(text))
        self.assertIn("Jane Doe (Engineer)", out)
        self.assertIn("Python \\ Go", out)
        self.assertIn("line 119", out)

    def test_tracker_dedupes(self):
        import csv
        import os
        import tempfile
        from jobhunt import tracker
        with tempfile.TemporaryDirectory() as d:
            os.environ["JOBHUNT_HOME"] = d
            try:
                job = {"title": "Dev", "company": "X", "location": "Dublin", "url": "http://a", "work_mode": "in-person", "score": 5}
                self.assertEqual(tracker.record([job], "hybrid"), 1)
                self.assertEqual(tracker.record([job], "hybrid"), 0)
                rows = list(csv.DictReader(open(tracker.csv_path())))
                self.assertEqual((rows[0]["country"], rows[0]["work_mode"]), ("Ireland", "hybrid"))
            finally:
                del os.environ["JOBHUNT_HOME"]
