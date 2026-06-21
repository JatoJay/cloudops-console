import { AppShell } from "@/components/app-shell";
import { KubernetesHistory } from "@/components/kubernetes-history";
import { LoginScreen } from "@/components/login-screen";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function KubernetesHistoryPage() {
  const insforge = await createInsForgeServerClient();
  const { data } = await insforge.auth.getCurrentUser();
  const user = data?.user;

  if (!user) return <LoginScreen />;
  return (
    <AppShell user={{ email: user.email }}>
      <KubernetesHistory userId={user.id} />
    </AppShell>
  );
}
