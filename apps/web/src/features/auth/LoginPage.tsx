import { useForm } from "react-hook-form";
import { z } from "zod";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Activity } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";

const schema = z.object({
  email: z.string().email("Zadejte platný e-mail"),
  password: z.string().min(1, "Zadejte heslo"),
});

type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<FormValues>({
    defaultValues: { email: "", password: "" },
  });

  if (loading) return <PageLoader />;
  if (user) return <Navigate to="/" replace />;

  async function onSubmit(values: FormValues) {
    setError(null);
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      const fieldErrors = parsed.error.flatten().fieldErrors;
      if (fieldErrors.email?.[0]) form.setError("email", { message: fieldErrors.email[0] });
      if (fieldErrors.password?.[0]) form.setError("password", { message: fieldErrors.password[0] });
      return;
    }
    try {
      await login(parsed.data.email, parsed.data.password);
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.status === 401 ? "Neplatné přihlašovací údaje" : err.message);
      } else {
        setError("Přihlášení se nezdařilo");
      }
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4">
      <div className="pointer-events-none absolute inset-0 bg-grid-fade" />
      <Card className="relative z-10 w-full max-w-md animate-fade-up shadow-glow">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <Activity className="h-6 w-6" />
          </div>
          <CardTitle className="font-display text-2xl">ApplyMind</CardTitle>
          <CardDescription>Přihlaste se ke svému AI náborovému agentovi</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input id="email" type="email" autoComplete="username" {...form.register("email")} />
              {form.formState.errors.email ? (
                <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Heslo</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...form.register("password")}
              />
              {form.formState.errors.password ? (
                <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>
              ) : null}
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button className="w-full" type="submit" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting ? "Přihlašuji…" : "Přihlásit se"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
