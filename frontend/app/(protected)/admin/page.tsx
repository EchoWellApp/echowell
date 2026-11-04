"use client";
// Admin (TRD 11 §4.10, UX-210..UX-219; TRD 04 FE-034: non-admins see AccessDenied and no admin
// API call is made).
import { AccessDenied } from "@/components/AccessDenied/AccessDenied";
import { AdminPanel } from "@/components/AdminPanel/AdminPanel";
import { useAuth } from "@/lib/AuthProvider";
import { useDocumentTitle } from "@/lib/hooks";
import { isAdmin } from "@/lib/roles";
import { ADMIN_TITLE } from "@/lib/wording";

export default function AdminPage() {
  useDocumentTitle(ADMIN_TITLE);
  const { user } = useAuth();
  if (!isAdmin(user?.role)) return <AccessDenied />;
  return (
    <div className="stack">
      <h1>{ADMIN_TITLE}</h1>
      <AdminPanel />
    </div>
  );
}
