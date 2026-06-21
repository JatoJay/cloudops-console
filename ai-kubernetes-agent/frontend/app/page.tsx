import { AppShell } from "@/components/app-shell";
import { LoginScreen } from "@/components/login-screen";
import { ProductLanding } from "@/components/product-landing";
import { createInsForgeServerClient } from "@/lib/insforge/server";

export default async function Home() {
  const insforge = await createInsForgeServerClient();
  const { data } = await insforge.auth.getCurrentUser();
  const user = data?.user;

  if (!user) return <LoginScreen />;
  return (
    <AppShell user={{ email: user.email }}>
      <ProductLanding />
    </AppShell>
  );
}
