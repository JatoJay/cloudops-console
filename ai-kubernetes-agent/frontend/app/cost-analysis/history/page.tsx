import { AnalysisHistory } from "@/components/analysis-history";
import { AppShell } from "@/components/app-shell";
import { LoginScreen } from "@/components/login-screen";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function CostHistoryPage() {
  const insforge = await createInsForgeServerClient();
  const { data } = await insforge.auth.getCurrentUser();
  const user = data?.user;

  if (!user) return <LoginScreen />;
  return (
    <AppShell user={{ email: user.email }}>
      <AnalysisHistory userId={user.id} />
    </AppShell>
  );
}
