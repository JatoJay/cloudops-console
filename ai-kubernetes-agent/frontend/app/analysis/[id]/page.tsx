import { AnalysisReport } from "@/components/analysis-report";
import { AppShell } from "@/components/app-shell";
import { LoginScreen } from "@/components/login-screen";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const [{ id }, insforge] = await Promise.all([params, createInsForgeServerClient()]);
  const { data } = await insforge.auth.getCurrentUser();
  const user = data?.user;

  if (!user) return <LoginScreen />;
  return (
    <AppShell user={{ email: user.email }}>
      <AnalysisReport analysisId={id} userId={user.id} />
    </AppShell>
  );
}
