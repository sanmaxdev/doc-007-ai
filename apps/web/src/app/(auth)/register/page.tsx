import { AuthForm } from "@/components/auth/auth-form";

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary/30 p-6">
      <AuthForm mode="register" />
    </div>
  );
}
