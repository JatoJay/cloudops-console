import { AppShell } from "@/components/app-shell";
import { CloudConnections } from "@/components/cloud-connections";
import { LoginScreen } from "@/components/login-screen";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function ConnectCloudPage() {
  const insforge = await createInsForgeServerClient();
  const { data } = await insforge.auth.getCurrentUser();
  if (!data?.user) return <LoginScreen />;
  return <AppShell user={{ email: data.user.email }}><CloudConnections /></AppShell>;
}
