"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

const LABELS: Record<string, string> = { google: "Google", github: "GitHub" };

export function OAuthButtons() {
  const [providers, setProviders] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .oauthProviders()
      .then((r) => setProviders(r.providers))
      .catch(() => setProviders([]));
  }, []);

  if (providers.length === 0) return null;

  async function go(provider: string) {
    setBusy(true);
    try {
      const redirectUri = `${window.location.origin}/oauth/${provider}/callback`;
      const { authorize_url, state } = await api.oauthAuthorize(provider, redirectUri);
      sessionStorage.setItem("oauth_state", state);
      window.location.assign(authorize_url);
    } catch {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>
      {providers.map((p) => (
        <Button
          key={p}
          type="button"
          variant="outline"
          className="w-full"
          disabled={busy}
          onClick={() => go(p)}
        >
          Continue with {LABELS[p] ?? p}
        </Button>
      ))}
    </div>
  );
}
