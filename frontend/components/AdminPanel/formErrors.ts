// Maps an ApiError to field and form messages by `code` and `errors[].field` (TRD 04 FE-079,
// TRD 11 UX-207). Never branches on title or detail text.
import { ADMIN_ERROR } from "@/lib/wording";
import { ApiError } from "@/services/api";

export interface FormErrors {
  fields: Record<string, string>;
  form: string | null;
}

/** "body.email" / "email" → "email". */
const leaf = (field: string) => field.split(".").pop() ?? field;

export function formErrorsFrom(error: unknown, known: readonly string[]): FormErrors {
  const fields: Record<string, string> = {};
  if (!(error instanceof ApiError)) return { fields, form: ADMIN_ERROR.generic };
  for (const e of error.errors) {
    const f = leaf(e.field);
    if (known.includes(f) && !fields[f]) fields[f] = e.message;
  }
  switch (error.code) {
    case "EMAIL_ALREADY_EXISTS":
      if (known.includes("email"))
        return { fields: { ...fields, email: ADMIN_ERROR.emailExists }, form: null };
      return { fields, form: ADMIN_ERROR.emailExists };
    case "PASSWORD_POLICY_VIOLATION":
      if (known.includes("password"))
        return {
          fields: { ...fields, password: fields.password ?? ADMIN_ERROR.passwordPolicy },
          form: null,
        };
      return { fields, form: ADMIN_ERROR.passwordPolicy };
    case "LAST_ADMIN":
      return { fields, form: ADMIN_ERROR.lastAdmin };
    case "FORBIDDEN":
      return { fields, form: ADMIN_ERROR.forbidden };
    case "VALIDATION_ERROR":
      return {
        fields,
        form: Object.keys(fields).length > 0 ? null : ADMIN_ERROR.invalid,
      };
    default:
      return { fields, form: ADMIN_ERROR.generic };
  }
}
