Slide 1: Title Slide
From Batch Files to Building LLMs A developer’s journey from scripting to architecting a personal AI assistant — powered by RAG and local LLMs.

🖼️ Suggested image: The conceptual header image I generated earlier — retro computer → Docker containers → AI brain.

🖼️ Slide 2: The Humble Beginnings
Batch Files & Echo Statements I started with .bat scripts. They automated tasks, deleted temp files, and printed “Hello World.” It was simple, but it sparked something.

🖼️ Suggested image: A retro terminal window with echo Hello World.

🖼️ Slide 3: Leveling Up
Bash, Python & Containers Bash gave me control. Python gave me clarity. Then came Docker — suddenly I wasn’t just scripting, I was orchestrating services.

🖼️ Suggested image: Docker whale lifting containers labeled “Python”, “Bash”, “Obsidian”.

🖼️ Slide 4: The Problem
My Notes Were Silent I had years of notes in Obsidian. But searching them was clunky. I wanted to ask: “What did I work on last week?” and get an answer.

🖼️ Suggested image: A vault of notes with a speech bubble saying “I wish I could talk…”

🖼️ Slide 5: Enter RAG
Retrieval-Augmented Generation I built a pipeline:

Chunk notes

Embed with Ollama

Store in ChromaDB

Retrieve relevant context

Feed into PH3 model

🖼️ Suggested image: Architectural diagram showing RAG flow (Obsidian → ChromaDB → Ollama → Answer)

🖼️ Slide 6: CI/CD Magic
Gitea + Makefile + Docker Compose Every push rebuilds the stack. Notes are ingested automatically. I query my assistant like a diary librarian.

🖼️ Suggested image: Gitea logo triggering build arrows to Docker containers.

🖼️ Slide 7: The Result
A Personal AI Assistant I type:

“Summarize last week” It responds with context-aware insights. I follow links like [[2025-12-01 - Interview Prep]] and jump straight into the right note.

🖼️ Suggested image: Terminal REPL with a natural language query and AI response.

🖼️ Slide 8: Closing
Curiosity → Architecture What started as a batch file became a full-stack AI system. If you’re scripting today, don’t underestimate where it might lead.

🖼️ Suggested image: Timeline from batch file → Docker → RAG → AI assistant.