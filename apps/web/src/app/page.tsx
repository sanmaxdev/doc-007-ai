import { FileText, MessageSquareQuote, ShieldCheck, Sparkles } from "lucide-react";

const features = [
  { icon: FileText, label: "Upload PDF, TXT & Markdown" },
  { icon: Sparkles, label: "Async extract → chunk → embed" },
  { icon: MessageSquareQuote, label: "Grounded answers with citations" },
  { icon: ShieldCheck, label: "Workspace-isolated & secure" },
];

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="mx-auto max-w-2xl text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          Phase 0 · Foundation scaffold
        </span>

        <h1 className="mt-6 text-5xl font-bold tracking-tight text-foreground">
          DOC<span className="text-primary">-007-</span>AI
        </h1>

        <p className="mt-4 text-lg text-muted-foreground">
          A multi-tenant AI knowledge base for businesses. Upload your documents,
          ask questions, and get answers grounded in — and cited from — your own
          sources.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {features.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-3 rounded-lg border border-border bg-card p-4 text-left text-sm text-card-foreground"
            >
              <Icon className="h-5 w-5 text-primary" />
              {label}
            </div>
          ))}
        </div>

        <p className="mt-10 text-sm text-muted-foreground">
          API:{" "}
          <a className="text-primary underline-offset-4 hover:underline" href="http://localhost:8000/docs">
            localhost:8000/docs
          </a>
        </p>
      </div>
    </main>
  );
}
