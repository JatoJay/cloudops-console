import { AppShell } from "@/components/app-shell";
import { ClusterConnections } from "@/components/cluster-connections";
import { LoginScreen } from "@/components/login-screen";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function ConnectClusterPage() {
  const insforge = await createInsForgeServerClient();
  const { data } = await insforge.auth.getCurrentUser();
  if (!data?.user) return <LoginScreen />;
  return <AppShell user={{ email: data.user.email }}><ClusterConnections /></AppShell>;
}
