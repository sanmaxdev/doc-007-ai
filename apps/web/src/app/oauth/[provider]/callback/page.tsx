"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

function CallbackInner() {
  const params = useParams<{ provider: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const [view, setView] = useState({ errored: false, message: "Completing sign-in…" });

  useEffect(() => {
    const provider = params.provider;
    const code = search.get("code");
    const state = search.get("state");
    const oauthError = search.get("error");
    const expectedState = sessionStorage.getItem("oauth_state");

    const failure = oauthError
      ? "Sign-in was cancelled."
      : !code
        ? "Missing authorization code."
        : !state || state !== expectedState
          ? "Sign-in could not be verified. Please try again."
          : null;

    if (failure) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time validation result
      setView({ errored: true, message: failure });
      return;
    }

    let cancelled = false;
    const redirectUri = `${window.location.origin}/oauth/${provider}/callback`;
    api
      .oauthCallback(provider, code as string, redirectUri)
      .then(async (tokens) => {
        if (cancelled) return;
        useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
        const user = await api.me();
        useAuthStore.getState().setUser(user);
        sessionStorage.removeItem("oauth_state");
        router.replace("/dashboard");
      })
      .catch(() => {
        if (!cancelled) {
          setView({ errored: true, message: "Could not complete sign-in. Please try again." });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-4 p-8 text-center">
          <p
            className={view.errored ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
          >
            {view.message}
          </p>
          {view.errored && (
            <Button variant="outline" onClick={() => router.replace("/login")}>
              Back to sign in
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <CallbackInner />
    </Suspense>
  );
}
