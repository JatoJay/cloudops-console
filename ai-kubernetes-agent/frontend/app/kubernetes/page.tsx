import { AppShell } from "@/components/app-shell";
import { Dashboard } from "@/components/dashboard";
import { LoginScreen } from "@/components/login-screen";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function KubernetesPage() {
  const insforge = await createInsForgeServerClient();
  const { data } = await insforge.auth.getCurrentUser();
  const user = data?.user;

  if (!user) return <LoginScreen />;
  return (
    <AppShell user={{ email: user.email }}>
      <Dashboard userId={user.id} />
    </AppShell>
  );
}
