"""Tailor CV and cover letter to a job, preserving the user's tone."""
SYSTEM = ("You are an expert career writer. Never invent employers, degrees, dates or skills the candidate "
          "does not have; only reorder, emphasise and rephrase real experience. Match the candidate's own "
          "writing tone and voice as shown in their original cover letter.")

MARK = "=====COVER LETTER====="


def build_prompt(cv, letter, job):
    return f"""Job: {job['title']} at {job['company']} ({job['location']})
Job description:
{job['description'][:4000]}

Candidate's original CV:
{cv}

Candidate's original cover letter (this shows the tone to keep):
{letter}

Write (1) an optimised CV tailored to this job, then a line containing exactly {MARK}
then (2) a new cover letter for this job in the same tone as the original. Output plain text only."""


def tailor(provider, cv, letter, job):
    out = provider.complete(SYSTEM, build_prompt(cv, letter, job))
    cv_out, _, letter_out = out.partition(MARK)
    return {"cv": cv_out.strip(), "cover_letter": letter_out.strip()}
