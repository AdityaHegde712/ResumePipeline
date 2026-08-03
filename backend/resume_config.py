"""
Resume LaTeX Section Templates and Configuration.

This module provides importable LaTeX sections extracted from template_blank.tex,
plus topmatter and bottommatter templates for composing resume documents.
"""

import re
from pathlib import Path


def escape_ampersands(text: str) -> str:
    """Escape any unescaped '&' characters to '\\&' for LaTeX compatibility."""
    if not text:
        return ""
    return re.sub(r'(?<!\\)&', r'\&', text)


# Boilerplate
topmatter = r"""%-------------------------
% Resume in Latex
% Author : Jake Gutierrez
% Based off of: https://github.com/sb2nov/resume
% License : MIT
%------------------------

\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{xcolor}


%----------FONT OPTIONS----------
% sans-serif
% \usepackage[sfdefault]{FiraSans}
% \usepackage[sfdefault]{roboto}
% \usepackage[sfdefault]{noto-sans}
% \usepackage[default]{sourcesanspro}

% serif
% \usepackage{CormorantGaramond}
% \usepackage{charter}


\pagestyle{fancy}
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-0.5in}
\addtolength{\textheight}{1.1in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
\vspace{-13pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-7pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\pdfgentounicode=1

\newcommand{\lt}{<}
\newcommand{\gt}{>}


%-------------------------
% Custom commands
\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubSubheading}[2]{
    \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-6pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
% \newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}, itemsep=0pt, parsep=0pt, topsep=0pt]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

\newcommand{\resumeLink}[1]{\href{#1}{\textcolor{blue}{Link}}}

%-------------------------------------------
%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%


\begin{document}
\textcolor{blue}{\tiny }
\begin{center}
    \vspace{-35pt}
    \textbf{\Huge \scshape Aditya Hegde} \\ \vspace{1pt}
    {\small \textit{Ideate $\rightarrow$ Build $\rightarrow$ Iterate}} \\ \vspace{2pt}
    \small San Jose, CA 
    $|$ 408-396-6553 
    $|$ \href{mailto:aditya.hegde@sjsu.edu}{\textcolor{blue}{aditya.hegde@sjsu.edu}} 
    $|$ \href{https://www.linkedin.com/in/aditya-hegde712} {\textcolor{blue}{linkedin.com/in/aditya-hegde712/}}
    $|$ \href{https://adityahegde712.github.io/}{\textcolor{blue}{adityahegde712.github.io}}
\end{center}"""

# Education
education = r"""\section{\textbf{Education}}
  \resumeSubHeadingListStart
    \resumeSubheading
      {San Jose State University}{San Jose, CA}
      {Master of Science in Artificial Intelligence (GPA: 4.0)}{Aug 2025 -- May 2027 (Expected)}
    \vspace{-3pt}
    \resumeSubheading
      {Woxsen University}{Telangana, India}
      {Bachelor of Technology in Computer Science Engineering (GPA: 3.73)}{Sep 2021 -- May 2025}
      \vspace{-8pt}
      \resumeSubSubheading
      {Dean's List: 8 semesters}{}\\
      \vspace{2pt}
      \textit{\small Published Researcher: 2 peer-reviewed papers (IEEE ICEPES 2024, Springer ICETSS 2026)}
  \resumeSubHeadingListEnd"""

# Skills
skills_top = r"""\section{\textbf{Technical Skills}}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
"""
skills_bullet = r"\textbf{{{type}}}: {skills} \\"
skills_bottom = r"""
    }}
 \end{itemize}"""

# Experience
experience_top = r"""\vspace{-10pt}
\section{\textbf{Experience}}
  \resumeSubHeadingListStart
"""
experience_entry_top = r"""
    \resumeSubheading
      {{{experience_name}}}{{{experience_start_end}}}
      {{{company_name}}}{{{location}}}
      \resumeItemListStart"""
experience_entry_bullet = r"\resumeItem{{{bullet}}}"
experience_entry_bottom = r"""
      \resumeItemListEnd
"""
experience_bottom = r"""
  \resumeSubHeadingListEnd
"""

# Projects
projects_top = r"""\vspace{-3pt}
\section{\textbf{Projects}}
  \resumeSubHeadingListStart
  \vspace{-2pt}"""
project_entry_top = r"""
    \resumeProjectHeading
        {{\textbf{{{project_name}}} $|$ \emph{{{tech_stack}}}}}{{\resumeLink{{{link}}}}}
        \resumeItemListStart
"""
project_entry_bullet = r"\resumeItem{{{bullet}}}"
project_entry_bottom = r"""
        \resumeItemListEnd"""
project_entry_separator = r"\vspace{-2pt}"
project_bottom = r"""
  \resumeSubHeadingListEnd"""

# Leadership
leadership = r"""\section{\textbf{Campus Involvement and Leadership}}
  \resumeSubHeadingListStart
  % \vspace{-8pt}
    \resumeSubheading
      {Chief Projects Officer, AI\&ML Club}{Feb 2026 -- Present}
      {San Jose State University}{San Jose, CA}
      \resumeItemListStart
        \resumeItem{Recruited and leading a \textbf{team of 8 project officers}.}
        \resumeItem{Managed over \textbf{17 projects}, spanning \textbf{70 active project members} and multiple GitHub repositories.}
        \resumeItem{Coordinated meetings and secured collaborations with companies for \textbf{5 industry-led Club projects}}
      \resumeItemListEnd
    \resumeSubHeadingListEnd"""

# Publications
publications = r"""\section{Publications and Awards}
\resumeItemListStart
\resumeItem{A. Baggu, A. Hegde, H. Morayya, S. A. Yallapragada, and H. Mazumdar, \textit{“Machine Learning-Based Space Risk Management: Asteroid and Solar Flare Prediction,”} 2024 IEEE 3rd International Conference on Electrical Power and Energy Systems (ICEPES), Bhopal, India, 2024, pp. 1–6, \href{https://doi.org/10.1109/ICEPES60647.2024.10653497}{doi: 10.1109/ICEPES60647.2024.10653497}.}
\resumeItem{Baggu, A., Hegde, A., Morayya, H., Kumar, L., Sattarapu, P., Yallapragada, S.A. (2026). \textit{"Deep Learning Based Dementia Detection on MRI Data."} In: Pal, S., Malhotra, S., Gupta, I., Kumar, A. (eds) Emerging Technology and Sustainable Solutions. ICETSS 2024. Communications in Computer and Information Science, vol 2610. Springer, Cham. \href{https://doi.org/10.1007/978-3-032-11488-4_15}{doi: 10.1007/978-3-032-11488-4\_15}}
\resumeItemListEnd"""

bottommatter = r"""\end{document}"""


if __name__ == "__main__":
    temp_dir = Path(__file__).parent / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Assemble Technical Skills section
    raw_skills = [
        ("Languages", "Python, C++ (proficient), JavaScript, HTML/CSS"),
        ("ML/AI Frameworks", "PyTorch, TensorFlow, ONNX, Scikit-Learn, OpenCV, Keras, Transformers"),
        ("Edge AI & Deployment", "Model Pruning, Static Graph Models (ONNX, TFLite), Quantization, ByteTrack, Docker"),
        ("AI Agents & LLMs", "Agent Workflows, ReAct, Model APIs, LLM Integration, Multi-Agent Orchestration"),
        ("Cloud & Infrastructure", "AWS (ECS Fargate, Lambda, EC2, CloudWatch, S3), Terraform, GCP, GitHub CI/CD"),
        ("Backend & Tools", "REST APIs, Flask, FastAPI, Django, Redis, SQL, Git, Linux"),
    ]
    skills_lines = [
        skills_bullet.format(type=escape_ampersands(stype), skills=escape_ampersands(sskills))
        for stype, sskills in raw_skills
    ]
    skills_section = skills_top + "\n".join(skills_lines) + skills_bottom

    # 2. Assemble Experience section (supports multiple experience entries)
    sample_experiences = [
        {
            "role": "Data Scientist Intern",
            "dates": "Mar 2024 -- Jul 2024",
            "company": "SUHORA Technologies Pvt. Ltd.",
            "location": "Uttar Pradesh, India",
            "bullets": [
                r"Built a \textbf{real-time vision pipeline} for maritime surveillance, processing \textbf{900+ SAR and optical satellite images} while sustaining over \textbf{95\% evaluation accuracy} and improving detection performance by \textbf{40\%+ mAP}.",
                r"Engineered a \textbf{C\#+Python preprocessing system} with \textbf{parallelized GPU usage}, runtime memory guards, and overflow controls, reducing batch inference latency from \textbf{7 minutes to sub-1 minute} for deployment.",
                r"Stress-tested the pipeline against \textbf{15B-pixel batches}, achieved \textbf{45-second processing per 10,000 km\textsuperscript{2} image}, and built a \textbf{fault-tolerant ingestion system} monitoring NAS for continued high-resolution geospatial input.",
                r"Produced \textbf{GIS-compatible GeoJSON outputs} via \textbf{overlap-aware postprocessing}, integrated \textbf{structured logging} with automated exception reporting for rapid debugging, collaborating with engineers to ship models.",
            ],
        }
    ]

    exp_entries = []
    for exp in sample_experiences:
        entry = (
            experience_entry_top.format(
                experience_name=escape_ampersands(exp["role"]),
                experience_start_end=escape_ampersands(exp["dates"]),
                company_name=escape_ampersands(exp["company"]),
                location=escape_ampersands(exp["location"]),
            )
            + "\n"
            + "\n".join([experience_entry_bullet.format(bullet=escape_ampersands(b)) for b in exp["bullets"]])
            + experience_entry_bottom
        )
        exp_entries.append(entry)

    experience_section = (
        experience_top
        + "".join(exp_entries)
        + experience_bottom
    )

    # 3. Assemble Projects section
    sample_projects = [
        {
            "name": "Sentry: Real-Time Threat Detection Platform",
            "tech": "Python, PyTorch, ONNX, AWS, Terraform, Docker",
            "link": "https://github.com/Aero-inc/sentry",
            "bullets": [
                r"Designed \textbf{3-stage cascaded inference pipeline} annotation, model routing, specialist analysis using \textbf{ONNX models}, reducing compute load via frame sampling and \textbf{confidence-gated specialist invocation}.",
                r"Architected, deployed full cloud infrastructure as code with \textbf{Terraform} \textbf{ECS Fargate, ALB, CloudFront, S3, and ElastiCache Redis} with a \textbf{graceful in-memory fallback} for stream-state continuity during outages.",
                r"\textbf{Modified, trained, tuned a YOLO model} for proximity detection identifying potential violence, built a \textbf{CI/CD pipeline} with GitHub Actions for automated build, test, and \textbf{Dockerized container deployment}.",
            ],
        },
        {
            "name": "PPE Detection on Edge Hardware (SiMa.ai)",
            "tech": "Python, PyTorch, YOLO, ONNX, W&B",
            "link": "https://github.com/AdityaHegde712/Industrial-Safety-Detection",
            "bullets": [
                r"Led a \textbf{4-person team} building independent \textbf{PPE-detection models} in a \textbf{1-month sprint} coordinated with \textbf{SiMa.ai's product team}, overseeing \textbf{validation methodology} and integrating results across all four tracks.",
                r"Conducted systematic hyperparameter search \textbf{18 experiments}: 3 model sizes, 3 learning rates, 2 optimizers, class-imbalance strategy using \textbf{Albumentations oversampling}, reaching \textbf{0.80 mAP@0.5} on the validation set.",
                r"Verified trimmed \textbf{ONNX export} to a \textbf{static input graph} for \textbf{SiMa.ai hardware constraints}, integrating \textbf{ByteTrack} for multi-object tracking, maintaining direct communication with SiMa.ai throughout development.",
            ],
        },
        {
            "name": "Multi-Agent Orchestration Framework",
            "tech": "Python, YAML, Agentic Systems Design",
            "link": "https://github.com/AdityaHegde712/agent-setup",
            "bullets": [
                r"Architected a \textbf{dynamic agent orchestration framework} \textbf{(2 primary agents, 18 sub-agents)} with \textbf{scoped execution budgets}, \textbf{enforced permission boundaries}, actively used and refined in daily workflows.",
                r"Designed a \textbf{confidence-based autonomy system} with \textbf{per-agent alignment scores} governing operating modes (conservative, predictive, autonomous), with \textbf{hard-restricted destructive operations} regardless of trust level.",
                r"Built a \textbf{dynamic synthesis system} generating bespoke, \textbf{minimum-permission agents} for uncovered task gaps, \textbf{23 custom skills} and structured task-logging \textbf{PLAN/TASKS/STATUS} for full delegation traceability.",
            ],
        },
    ]

    project_entries = []
    for p in sample_projects:
        entry = (
            project_entry_top.format(
                project_name=escape_ampersands(p["name"]),
                tech_stack=escape_ampersands(p["tech"]),
                link=escape_ampersands(p["link"]),
            )
            + "\n".join([project_entry_bullet.format(bullet=escape_ampersands(b)) for b in p["bullets"]])
            + project_entry_bottom
        )
        project_entries.append(entry)

    projects_section = (
        projects_top
        + ("\n" + project_entry_separator + "\n").join(project_entries)
        + project_bottom
    )

    variables = {
        "topmatter.tex": topmatter,
        "education.tex": education,
        "technical_skills.tex": skills_section,
        "experience.tex": experience_section,
        "projects.tex": projects_section,
        "leadership.tex": leadership,
        "publications.tex": publications,
        "bottommatter.tex": bottommatter,
    }

    print(f"Writing section variables to {temp_dir}:")
    for filename, content in variables.items():
        filepath = temp_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f" - Saved {filename} ({len(content)} chars)")

    # Render complete document to test assembly
    full_doc = "\n\n".join([
        topmatter,
        education,
        skills_section,
        experience_section,
        projects_section,
        leadership,
        publications,
        bottommatter,
    ])
    full_path = temp_dir / "full_resume_test.tex"
    full_path.write_text(full_doc, encoding="utf-8")
    print(f" - Saved full_resume_test.tex ({len(full_doc)} chars)")
    print("Testing output generation complete!")

