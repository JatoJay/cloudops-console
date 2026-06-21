import { AppShell } from "@/components/app-shell";
import { CloudDashboard } from "@/components/cloud-dashboard";
import { LoginScreen } from "@/components/login-screen";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function CostAnalysisPage() {
  const insforge = await createInsForgeServerClient();
  const { data } = await insforge.auth.getCurrentUser();
  const user = data?.user;

  if (!user) return <LoginScreen />;
  return (
    <AppShell user={{ email: user.email }}>
      <CloudDashboard userId={user.id} />
    </AppShell>
  );
}
