import Link from "next/link";

function Wordmark() {
  return (
    <span className="font-display text-base font-bold tracking-tight">
      DOC<span className="text-primary">-007-</span>AI
    </span>
  );
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-[100dvh] lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-border bg-card p-12 lg:flex">
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-50 mask-radial-faded" />
        <div className="pointer-events-none absolute -left-24 top-1/3 h-72 w-72 rounded-full bg-primary/10 blur-[110px]" />

        <Link href="/" className="relative w-fit" aria-label="DOC-007-AI home">
          <Wordmark />
        </Link>

        <div className="relative max-w-md">
          <h1 className="font-display text-4xl font-bold leading-[1.1] tracking-tight">
            Answers your documents can prove.
          </h1>
          <p className="mt-4 text-muted-foreground">
            Grounded, cited, and workspace-isolated. The knowledge base that refuses to guess.
          </p>
          <div className="mt-8 inline-flex items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-2 font-mono text-xs text-muted-foreground">
            <span className="text-primary">[1]</span>
            employee-handbook.pdf · p.12 · 0.91
          </div>
        </div>

        <p className="relative font-mono text-xs text-muted-foreground">
          Multi-tenant RAG · grounded answers with citations
        </p>
      </div>

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <Link href="/" className="mb-8 flex justify-center lg:hidden" aria-label="DOC-007-AI home">
            <Wordmark />
          </Link>
          {children}
        </div>
      </div>
    </div>
  );
}
