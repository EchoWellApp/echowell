// "/" redirects to the Residents overview (TRD 04 §4.2).
import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/residents");
}
