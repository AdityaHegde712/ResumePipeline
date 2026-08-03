<preparation>
At server startup:
Read profile.yaml, retain keys: experience, publications, skills, section_order (with fallback as topmatter, education, skills, projects, leadership, publications).
Read project_sweep: docs/PROJECT_SWEEP_SUMMARIES.md.

Read LLM_PROMPT, save as llm_prompt, can be templated as something like in `backend/llm_prompt.md`.
</preparation>

<live_behavior>
frontend_to_backend_request: send job_position, job_description, company_name, optional_company_description.

<request_processing>
Generate application_id: during runtime when a frontend-to-backend request is received, application_id saved as `application-{datetime_string}`

Construct company description string:

```sample_logic
company_desc_string = ""
if optional_company_description is not null:
company_desc_string = f"- COMPANY DESCRIPTION: {optional_company_description}\n"

```

Build llm_request: Fill available details into llm_prompt using string formatting. Details read during preparation phase and frontend_to_backend_request.
</request_processing>

backend_to_llm_request: Send llm_request to the LLM.

llm_response: Plaintext newline-separated sentences formatted as per system prompt.

<resume_construction>
I have placed reusable sections of the resume latex construction in a config py file called backend/resume_config.py so that reading a single tex file and making volatile or non-deterministic is not necessary. These variables can be imported, used, and substituted as per our needs. The merging logic is in the **main** section of this file. The only ambiguous or risky part is how the system prompt and the LLM are initialized so that it gives us clean and delimiter-friendly parse-able text to substitute for this construction logic.

The llm_response text will be read and parsed deterministically by string manipulation, to isolate: experience_bullets, (project_name + project_bullet) chunks.
Iterate through section_order (read from profile). For each standard key in the section_order, construct and fill the corresponding resume sections. Use helper functions so that plug and play is possible and code looks neat.
</resume_construction>

<post_processing>
The finished construction should be utf-8 encoded and saved as a .tex file in its respective application directory, `backend/data/applications/{application_id}/resume.tex`.

We know the path where it is saved. The .tex file is compiled by miktex using subprocess or something in the backend, and saved as `backend/data/applications/{application_id}/resume.pdf`.

Entire llm_response is saved as `backend/data/applications/{application_id}/llm_response.md`.
</post_processing>

backend_to_frontend_response: Response JSON, looks something like:

```
{
STATUS: 200,
llm_generation: OK,
Reconstruction: OK,
Saved: OK,
application_id: {application_id}.
}
```

(Responses need to be constructed according to which phase fails or if all phases work. Try/except blocks in backend logic would be needed.)

<frontend_behavior>

Reads response.
If any error, flag on front-end naming which phase fails. This is for me, it helps with debugging.
If no errors, show success.

If success,
Read `backend/data/applications/{application_id}/llm_response.md` and display in textbox for user to see.
Export buttons trigger a request to the backend with the received application id to serve the saved tex or pdf file, depending on what the user chooses.

</frontend_behavior>

</live_behavior>
