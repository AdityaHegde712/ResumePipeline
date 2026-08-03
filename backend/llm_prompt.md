<context>

- JOB TARGET: {job_position} at {company_name}
- JOB DESCRIPTION: {job_description}
  {company_desc_string}

- EXISTING SKILLS:

```
{skills}
```

- EXISTING WORK EXPERIENCE:

```
{experience}
```

- PROJECT SWEEP FILE:

```
{project_sweep_file_contents}
```

</context>

---

<instructions>

Perform the following tasks in order:

Output plain text only. Do NOT wrap the response in Markdown code fences (```) and do not use bold, italics, bullet glyphs (-, *, •), or any Markdown formatting other than the # / ## section markers shown.

TASK 1: REWRITE WORK EXPERIENCE
Rewrite 3-4 bullet points for each Work Experience entry to align closely with the target Job Description keywords and requirements.

TASK 2: SELECT & GENERATE PROJECTS

1. Evaluate all projects in the sweep file against the Job Description.
2. Select the top 3 most relevant projects and order them from most relevant to least relevant.
3. For each selected project, generate a header formatted as `## N. Project Name | tech_stack` (where `N` is the project's original index number from the sweep file), followed by 3-4 tailored bullet points.

TASK 3: SELECT AND INFER SKILLS

1. Evaluate the skills needed for the target Job Description keywords and requirements.
2. Rewrite the Skills section for both Types and Skills as necessary.

</instructions>

---

<output_format>
Provide the output in clean python-parseable plaintext, following this structure (the code fence below only illustrates the format — do NOT include fence markers in your response):

```
# Skills
type_1: skill_1, skill_2, skill_3
type_2: skill_1, skill_2, skill_3

# Experience

## Experience 1
bullet1_line
bullet2_line
bullet3_line
bullet4_line

## Experience 2
bullet1_line
bullet2_line
bullet3_line
bullet4_line

# Projects

## N1. Project_Name_1 | tech_stack_1 | -
bullet1_line
bullet2_line
bullet3_line
bullet4_line

## N2. Project_Name_2 | tech_stack_2 | -
bullet1_line
bullet2_line
bullet3_line
bullet4_line

## N3. Project_Name_3 | tech_stack_3 | -
bullet1_line
bullet2_line
bullet3_line
bullet4_line
```

</output_format>
