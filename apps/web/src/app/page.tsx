import {
  ArrowRight,
  BarChart3,
  Check,
  FileText,
  Lock,
  Quote,
  ScanSearch,
  ShieldCheck,
  Workflow,
  Zap,
} from "lucide-react";
import Link from "next/link";

import { Reveal } from "@/components/landing/reveal";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const GITHUB_URL = "https://github.com/sanmaxdev/doc-007-ai";

function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-display text-base font-bold tracking-tight", className)}>
      DOC<span className="text-primary">-007-</span>AI
    </span>
  );
}

/* The hero's product surface. A real, polished preview of the signature answer
   experience, not a generic dashboard mock. */
function AnswerPreview() {
  return (
    <div className="relative w-full">
      <div className="absolute -inset-px rounded-2xl bg-gradient-to-b from-primary/25 to-transparent opacity-60 blur-[2px]" />
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-2xl shadow-black/40">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
          <span className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-accent/70" />
          <span className="ml-2 font-mono text-xs text-muted-foreground">acme-hr / chat</span>
        </div>

        <div className="space-y-4 p-5">
          <div className="flex justify-end">
            <p className="max-w-[80%] rounded-lg rounded-br-sm bg-secondary px-3 py-2 text-sm">
              How many vacation days do full-time employees get?
            </p>
          </div>

          <div className="space-y-3">
            <p className="text-sm leading-relaxed">
              Full-time employees receive 25 days of paid vacation per year, with up to 5
              unused days carried over{" "}
              <span className="font-mono text-xs text-primary align-super">[1]</span>.
            </p>

            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/25 bg-accent/12 px-2.5 py-0.5 text-xs font-medium text-accent">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              High confidence
            </span>

            <div className="space-y-2 pt-1">
              {[
                { n: 1, doc: "employee-handbook.pdf", page: "p.12", score: "0.91" },
                { n: 2, doc: "leave-policy.md", page: "", score: "0.74" },
              ].map((c) => (
                <div
                  key={c.n}
                  className="rounded-lg border border-border bg-background/60 p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2 truncate text-xs font-medium">
                      <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="font-mono text-primary">[{c.n}]</span>
                      <span className="truncate">{c.doc}</span>
                      {c.page && (
                        <span className="font-mono text-muted-foreground">{c.page}</span>
                      )}
                    </span>
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">
                      {c.score}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" aria-label="DOC-007-AI home">
          <Wordmark />
        </Link>
        <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
          <a href="#capabilities" className="transition-colors hover:text-foreground">
            Capabilities
          </a>
          <a href="#security" className="transition-colors hover:text-foreground">
            Security
          </a>
          <a href="#api" className="transition-colors hover:text-foreground">
            API
          </a>
          <a
            href={GITHUB_URL}
            className="transition-colors hover:text-foreground"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/login" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
            Sign in
          </Link>
          <Link href="/register" className={cn(buttonVariants({ size: "sm" }))}>
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid mask-radial-faded opacity-60" />
      <div className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[820px] -translate-x-1/2 rounded-full bg-primary/10 blur-[120px]" />
      <div className="relative mx-auto grid max-w-6xl gap-14 px-6 pb-24 pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-10 lg:pt-24">
        <div>
          <span className="inline-flex animate-fade-up items-center gap-2 rounded-full border border-border bg-card px-3 py-1 font-mono text-xs tracking-wide text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            MULTI-TENANT RAG KNOWLEDGE BASE
          </span>
          <h1
            className="mt-6 animate-fade-up font-display text-4xl font-bold leading-[1.05] tracking-tight text-balance sm:text-5xl lg:text-6xl"
            style={{ animationDelay: "60ms" }}
          >
            Answers your documents can prove.
          </h1>
          <p
            className="mt-5 max-w-xl animate-fade-up text-lg leading-relaxed text-muted-foreground"
            style={{ animationDelay: "120ms" }}
          >
            Turn your files into a private knowledge base that answers questions and cites
            every claim, down to the page.
          </p>
          <div
            className="mt-9 flex animate-fade-up flex-wrap items-center gap-3"
            style={{ animationDelay: "180ms" }}
          >
            <Link href="/register" className={cn(buttonVariants({ size: "lg" }))}>
              Get started
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/login"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              Sign in
            </Link>
          </div>
        </div>

        <div className="animate-fade-up" style={{ animationDelay: "240ms" }}>
          <AnswerPreview />
        </div>
      </div>
    </section>
  );
}

function Differentiator() {
  return (
    <section className="border-t border-border bg-card/30">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <Reveal className="max-w-2xl">
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Grounded, or it says so.
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
            Every answer is built only from your documents and carries its sources. When the
            documents do not hold the answer, DOC-007 tells you instead of inventing one.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-5 md:grid-cols-2">
          <Reveal delay={60}>
            <div className="h-full rounded-xl border border-border bg-card p-6">
              <div className="flex items-center gap-2 text-sm font-medium text-accent">
                <Quote className="h-4 w-4" />
                Cited from the source
              </div>
              <p className="mt-4 text-sm leading-relaxed">
                Expenses must be submitted within 30 days with an itemized receipt{" "}
                <span className="font-mono text-xs text-primary align-super">[1]</span>.
              </p>
              <p className="mt-3 font-mono text-xs text-muted-foreground">
                [1] expense-policy.pdf · p.4 · 0.88
              </p>
            </div>
          </Reveal>
          <Reveal delay={120}>
            <div className="h-full rounded-xl border border-dashed border-border bg-card p-6">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <ShieldCheck className="h-4 w-4" />
                No source, no guess
              </div>
              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                I couldn&apos;t find this in your documents.
              </p>
              <p className="mt-3 font-mono text-xs text-muted-foreground">
                relevance below threshold · 0 citations
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Retrieval debug",
    body: "Inspect the exact chunks, their scores, and the assembled prompt before any answer is generated.",
  },
  {
    icon: Workflow,
    title: "Async ingestion",
    body: "Extract, clean, chunk, embed. A visible status machine with graceful failure and reprocessing.",
  },
  {
    icon: Zap,
    title: "Streaming answers",
    body: "Responses stream token by token over Server-Sent Events as they are generated.",
  },
  {
    icon: BarChart3,
    title: "Analytics",
    body: "Answer rate, knowledge gaps, most-cited documents, and helpful or not-helpful feedback.",
  },
];

function Capabilities() {
  return (
    <section id="capabilities" className="border-t border-border">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <h2 className="max-w-2xl font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Everything a real knowledge base needs
          </h2>
        </Reveal>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          <Reveal className="md:col-span-2" delay={40}>
            <div className="flex h-full flex-col justify-between gap-6 rounded-xl border border-border bg-card p-7">
              <div>
                <h3 className="font-display text-xl font-semibold">Hybrid retrieval</h3>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
                  Dense vectors and keyword search, fused with reciprocal rank fusion. The
                  scores are on display, not hidden behind a black box.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3 font-mono text-xs">
                {[
                  { label: "dense", value: "0.54" },
                  { label: "lexical", value: "11" },
                  { label: "fused", value: "0.032" },
                ].map((s) => (
                  <div key={s.label} className="rounded-lg border border-border bg-background/60 p-3">
                    <div className="text-muted-foreground">{s.label}</div>
                    <div className="mt-1 text-base text-foreground">{s.value}</div>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>

          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={80 + i * 40}>
              <div className="h-full rounded-xl border border-border bg-card p-7">
                <f.icon className="h-5 w-5 text-primary" />
                <h3 className="mt-4 font-display text-lg font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const STEPS = [
  { k: "01", label: "Upload", note: "PDF, DOCX, text, markdown" },
  { k: "02", label: "Extract & chunk", note: "page-aware, token-sized" },
  { k: "03", label: "Embed", note: "stored in Qdrant" },
  { k: "04", label: "Retrieve", note: "hybrid, workspace-filtered" },
  { k: "05", label: "Cite", note: "answer with sources" },
];

function Pipeline() {
  return (
    <section className="border-t border-border bg-card/30">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            From upload to cited answer
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-5">
          {STEPS.map((s, i) => (
            <Reveal key={s.k} delay={i * 60}>
              <div className="h-full bg-card p-6">
                <div className="font-mono text-xs text-primary">{s.k}</div>
                <div className="mt-3 font-display text-base font-semibold">{s.label}</div>
                <div className="mt-1 font-mono text-xs text-muted-foreground">{s.note}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const GUARANTEES = [
  "Isolation at the SQL layer and the vector store, with membership checked on every request.",
  "Retrieved text is treated as data, never as instructions, so prompt injection stays contained.",
  "Passwords, API keys, and invite tokens are stored only as hashes.",
  "Per-key rate limits, per-workspace quotas, and an audit trail on every sensitive action.",
];

function Security() {
  return (
    <section id="security" className="border-t border-border">
      <div className="mx-auto grid max-w-6xl gap-12 px-6 py-24 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <Reveal>
          <Lock className="h-6 w-6 text-primary" />
          <h2 className="mt-5 font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Tenants never see each other
          </h2>
          <p className="mt-4 text-muted-foreground">
            Security is enforced in the data path, not bolted on after.
          </p>
        </Reveal>
        <Reveal delay={80}>
          <ul className="grid gap-px overflow-hidden rounded-xl border border-border bg-border">
            {GUARANTEES.map((g) => (
              <li key={g} className="flex items-start gap-3 bg-card p-5 text-sm leading-relaxed">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                <span>{g}</span>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}

function Api() {
  return (
    <section id="api" className="border-t border-border bg-card/30">
      <div className="mx-auto grid max-w-6xl gap-12 px-6 py-24 lg:grid-cols-2 lg:items-center lg:gap-16">
        <Reveal>
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            A public API for the rest of your stack
          </h2>
          <p className="mt-4 text-muted-foreground">
            Scoped API keys, per-key rate limits, and usage quotas. List documents, upload,
            and ask, all from one endpoint.
          </p>
          <Link
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
          >
            Read the source
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Reveal>
        <Reveal delay={80}>
          <div className="overflow-hidden rounded-xl border border-border bg-[hsl(220_16%_5%)] shadow-xl shadow-black/30">
            <div className="border-b border-white/10 px-4 py-2.5 font-mono text-xs text-white/40">
              POST /api/public/v1/ask
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-relaxed text-white/80">
              <code>
                <span className="text-white/40">$</span> curl -s api.doc007.ai/v1/ask{"\n"}
                {"  "}-H <span className="text-primary">{'"authorization: Bearer doc7_…"'}</span>{" "}
                \{"\n"}
                {"  "}-d{" "}
                <span className="text-accent">{'{"question":"What is our refund window?"}'}</span>
              </code>
            </pre>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Cta() {
  return (
    <section className="border-t border-border">
      <div className="mx-auto max-w-3xl px-6 py-28 text-center">
        <Reveal>
          <h2 className="font-display text-4xl font-bold tracking-tight text-balance sm:text-5xl">
            Put your documents to work.
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Stand up a grounded, cited knowledge base in minutes.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className={cn(buttonVariants({ size: "lg" }))}>
              Get started
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              View on GitHub
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-muted-foreground sm:flex-row">
        <Wordmark className="text-sm" />
        <div className="flex items-center gap-6">
          <Link href="/login" className="hover:text-foreground">
            Sign in
          </Link>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="hover:text-foreground">
            GitHub
          </a>
          <span className="font-mono text-xs">MIT</span>
        </div>
      </div>
    </footer>
  );
}

export default function Home() {
  return (
    <main className="min-h-[100dvh]">
      <Nav />
      <Hero />
      <Differentiator />
      <Capabilities />
      <Pipeline />
      <Security />
      <Api />
      <Cta />
      <Footer />
    </main>
  );
}
