import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "/Users/dongyeyuan/Desktop/YWP Labs/CourseMind/CourseMind";
const SKILL_DIR = "/Users/dongyeyuan/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.61513/skills/presentations";
const TMP_DIR = path.join(workspaceDir, "submission", ".deck-build");
const FINAL_PPTX = path.join(workspaceDir, "submission", "devpost", "CourseMind_AI_Builders_Hackathon_Deck_v2.pptx");
const RUNTIME_PYTHON = "/Users/dongyeyuan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";

const { resolvePresentationFont, finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href,
);

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const family = resolvePresentationFont();
const presentation = Presentation.create({
  slideSize: { width: 1280, height: 720 },
});

const colors = {
  ink: "#111827",
  muted: "#4B5563",
  light: "#F9FAFB",
  border: "#E5E7EB",
  primary: "#7C3AED",
  primarySoft: "#F3E8FF",
  green: "#059669",
};

function addBox(slide, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: style.fill ?? "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: family,
    fontSize: style.fontSize ?? 24,
    bold: style.bold ?? false,
    color: style.color ?? colors.ink,
    autoFit: "shrinkText",
  };
  return shape;
}

function addSlide({ title, subtitle, body, footer, notes }, slideNo) {
  const slide = presentation.slides.add();
  slide.background.fill = colors.light;
  addBox(slide, "CourseMind", { left: 72, top: 34, width: 240, height: 30 }, {
    fontSize: 18,
    bold: true,
    color: colors.primary,
  });
  addBox(slide, title, { left: 72, top: 86, width: 900, height: 74 }, {
    fontSize: 40,
    bold: true,
  });
  if (subtitle) {
    addBox(slide, subtitle, { left: 72, top: 162, width: 960, height: 54 }, {
      fontSize: 21,
      color: colors.muted,
    });
  }
  addBox(slide, body, { left: 72, top: subtitle ? 238 : 190, width: 1030, height: subtitle ? 350 : 410 }, {
    fontSize: 25,
    color: colors.ink,
  });
  if (footer) {
    addBox(slide, footer, { left: 72, top: 642, width: 880, height: 34 }, {
      fontSize: 15,
      color: colors.muted,
    });
  }
  addBox(slide, `${slideNo}`, { left: 1160, top: 642, width: 50, height: 28 }, {
    fontSize: 14,
    color: colors.muted,
  });
  slide.speakerNotes.textFrame.setText(notes ?? "");
}

const slides = [
  {
    title: "CourseMind",
    subtitle: "An AI study canvas for course materials",
    body: "CourseMind turns uploaded course materials into source-backed Q&A, visual concept cards, follow-up notes, quizzes, and weak-point review.\n\nBuilt for AI Builders Hackathon 2026.",
    footer: "Vue 3, FastAPI, PostgreSQL, pgvector, DashScope Qwen",
    notes: "Submission material based on repository README and Devpost AI Builders Hackathon requirements.",
  },
  {
    title: "Problem Statement",
    subtitle: "Students lose time deciding what to review",
    body: "Long PDFs and lecture notes hide the most important concepts.\n\nGeneric AI answers can be hard to trust without sources.\n\nFollow-up questions, notes, quizzes, and weak points often live in separate tools.",
    notes: "Problem derived from CourseMind project summary and intended student review workflow.",
  },
  {
    title: "Solution Overview",
    subtitle: "One workflow from material to review",
    body: "1. Upload course files.\n2. Ask grounded questions with cited sources.\n3. Generate a learning canvas.\n4. Expand one concept with follow-up questions.\n5. Create quizzes and review weak points.",
    notes: "Maps to Devpost solution overview and product workflow.",
  },
  {
    title: "Target Users",
    subtitle: "Students who need active review",
    body: "University students preparing for exams.\n\nOnline learners organizing course notes.\n\nBilingual learners working across English and Chinese materials.\n\nStudents who want AI support while keeping source traceability.",
    notes: "Target users from repository submission summary.",
  },
  {
    title: "Product Features",
    subtitle: "Core capabilities in the current build",
    body: "Document management for TXT, Markdown, and PDF.\n\nKnowledge base Q&A with source snippets.\n\nLearning canvas with concept cards and citations.\n\nFollow-up child cards, quizzes, and weak-point markers.\n\nEnglish and Simplified Chinese UI.",
    notes: "Current implemented product features from README.",
  },
  {
    title: "Technical Architecture",
    subtitle: "A full-stack RAG learning app",
    body: "Frontend: Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue I18n.\n\nBackend: FastAPI, SQLAlchemy, Alembic, JWT authentication.\n\nData: PostgreSQL 17 with pgvector.\n\nAI: DashScope Qwen and text-embedding-v3.\n\nDeployment: Docker Compose.",
    notes: "Architecture from README and project docs.",
  },
  {
    title: "AI Technologies Used",
    subtitle: "Retrieval and generation stay connected to course materials",
    body: "DashScope text-embedding-v3 embeds document chunks.\n\npgvector retrieves relevant chunks by semantic similarity.\n\nQwen generates answers, concept cards, follow-up explanations, and quiz content.\n\nThe UI shows sources and insufficient-context states where available.",
    notes: "AI usage disclosure from repository docs.",
  },
  {
    title: "Impact and Value",
    subtitle: "A more trustworthy review workflow",
    body: "Students spend less time finding key concepts.\n\nSource snippets make AI answers easier to verify.\n\nFollow-up behavior creates weak-point signals.\n\nThe canvas keeps notes, questions, quizzes, and review focus in one place.",
    notes: "Impact and value proposition for Devpost judging.",
  },
  {
    title: "Current Status",
    subtitle: "Ready for a judged prototype demo",
    body: "Built: authentication, document upload, RAG Q&A, learning canvas, AI chat, bilingual UI, Docker setup.\n\nLimits: no PPTX or DOCX parsing, no scanned PDF OCR, card-grid canvas instead of freeform drag-and-drop, real AI flows require DashScope credentials.",
    notes: "Current limits should stay visible for judging transparency.",
  },
  {
    title: "Future Roadmap",
    subtitle: "From prototype to daily study workspace",
    body: "Add PPTX, DOCX, scanned PDF, and image OCR support.\n\nAdd freeform drag-and-drop canvas organization.\n\nAdd spaced repetition and long-term learner memory.\n\nExport notes to Markdown, flashcards, or study plans.\n\nAdd instructor analytics for class-level weak points.",
    notes: "Roadmap from project summary and Devpost submission copy.",
  },
];

slides.forEach((slide, index) => addSlide(slide, index + 1));

const candidatePath = path.join(TMP_DIR, "coursemind_deck_candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 10,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
};
const fontPolicy = { basis: "design", families: [family] };
const expectedSlideSizeEmu = "12192000,6858000";

await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu",
    expectedSlideSizeEmu,
    "--validate-heading-fit",
  ],
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(TMP_DIR, "CourseMind_AI_Builders_Hackathon_Deck_v2.validation.json"),
});

for (let i = 0; i < presentation.slides.length; i += 1) {
  const slide = presentation.slides.get(i);
  const preview = await presentation.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(TMP_DIR, `slide-${i + 1}.png`), new Uint8Array(await preview.arrayBuffer()));
}

console.log(FINAL_PPTX);
