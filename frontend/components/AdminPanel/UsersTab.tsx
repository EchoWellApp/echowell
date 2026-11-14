"use client";
// Users tab: list, add user, role change, deactivate/reactivate (TRD 11 UX-211, UX-207, UX-227,
// UX-228; TRD 04 FE-079; FEAT-074-FR-03..FR-05).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { QueryState } from "@/components/SectionState/SectionState";
import { formatDateTimeShort } from "@/lib/format";
import { queryKeys } from "@/lib/queryKeys";
import type { Role, User, UserCreate, UserUpdate } from "@/lib/types";
import {
  ADMIN_ADD_USER,
  ADMIN_ADD_USER_SUBMIT,
  ADMIN_ADDING_USER,
  ADMIN_CANCEL,
  ADMIN_DEACTIVATE,
  ADMIN_ERROR,
  ADMIN_FIELD,
  ADMIN_NEVER,
  ADMIN_NO,
  ADMIN_REACTIVATE,
  ADMIN_ROLE_LABEL,
  ADMIN_USERS_COLUMNS,
  ADMIN_USERS_EMPTY,
  ADMIN_USERS_PANEL,
  ADMIN_YES,
  adminDeactivateConfirm,
  adminDeactivateName,
  adminReactivateName,
  adminRoleFor,
  adminUserAdded,
  adminUserUpdated,
} from "@/lib/wording";
import * as api from "@/services/api";
import styles from "./AdminPanel.module.css";
import { formErrorsFrom, type FormErrors } from "./formErrors";

const ROLES: Role[] = ["admin", "clinician", "researcher"];
const FIELDS = ["email", "display_name", "role", "password"] as const;
type Field = (typeof FIELDS)[number];
const NO_ERRORS: FormErrors = { fields: {}, form: null };

function AddUserForm({ onAdded }: { onAdded(email: string): void }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<UserCreate>({
    email: "",
    display_name: "",
    role: "clinician",
    password: "",
  });
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS);
  const create = useMutation({
    mutationFn: api.createUser,
    onSuccess: (user) => {
      setValues({ email: "", display_name: "", role: "clinician", password: "" });
      setErrors(NO_ERRORS);
      onAdded(user.email);
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminUsers() });
    },
    onError: (e) => setErrors(formErrorsFrom(e, FIELDS)),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const missing: Record<string, string> = {};
    for (const f of FIELDS) if (!String(values[f]).trim()) missing[f] = ADMIN_ERROR.required;
    if (Object.keys(missing).length > 0) {
      setErrors({ fields: missing, form: null });
      return;
    }
    setErrors(NO_ERRORS);
    create.mutate(values);
  }

  const set = (f: Field) => (v: string) => setValues((old) => ({ ...old, [f]: v }));
  const fieldProps = (f: Field) => {
    const err = errors.fields[f];
    return {
      id: `user-${f}`,
      className: styles.input,
      "aria-invalid": err ? true : undefined,
      "aria-describedby": err ? `user-${f}-error` : undefined,
    };
  };
  const fieldError = (f: Field) =>
    errors.fields[f] ? (
      <p id={`user-${f}-error`} className={styles.fieldError}>
        {errors.fields[f]}
      </p>
    ) : null;

  return (
    <section aria-labelledby="add-user-heading" className="stack">
      <h3 id="add-user-heading">{ADMIN_ADD_USER}</h3>
      <form className={styles.form} onSubmit={onSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor="user-email">{ADMIN_FIELD.email}</label>
          <input
            {...fieldProps("email")}
            type="email"
            autoComplete="off"
            value={values.email}
            onChange={(e) => set("email")(e.target.value)}
          />
          {fieldError("email")}
        </div>
        <div className={styles.field}>
          <label htmlFor="user-display_name">{ADMIN_FIELD.displayName}</label>
          <input
            {...fieldProps("display_name")}
            type="text"
            autoComplete="off"
            value={values.display_name}
            onChange={(e) => set("display_name")(e.target.value)}
          />
          {fieldError("display_name")}
        </div>
        <div className={styles.field}>
          <label htmlFor="user-role">{ADMIN_FIELD.role}</label>
          <select
            {...fieldProps("role")}
            value={values.role}
            onChange={(e) => set("role")(e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ADMIN_ROLE_LABEL[r]}
              </option>
            ))}
          </select>
          {fieldError("role")}
        </div>
        <div className={styles.field}>
          <label htmlFor="user-password">{ADMIN_FIELD.password}</label>
          <input
            {...fieldProps("password")}
            type="password"
            autoComplete="new-password"
            value={values.password}
            onChange={(e) => set("password")(e.target.value)}
          />
          {fieldError("password")}
        </div>
        <p role="alert" className={styles.formError}>
          {errors.form}
        </p>
        <div className={styles.actions}>
          <button type="submit" className="btn" disabled={create.isPending}>
            {create.isPending ? ADMIN_ADDING_USER : ADMIN_ADD_USER_SUBMIT}
          </button>
        </div>
      </form>
    </section>
  );
}

function ConfirmDeactivate(props: { user: User; onConfirm(): void; onCancel(): void }) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => cancelRef.current?.focus(), []);
  return (
    <div
      role="alertdialog"
      aria-labelledby="deactivate-text"
      aria-modal="false"
      className={styles.dialog}
    >
      <p id="deactivate-text">{adminDeactivateConfirm(props.user.email)}</p>
      <button type="button" className="btn" onClick={props.onConfirm}>
        {ADMIN_DEACTIVATE}
      </button>
      <button ref={cancelRef} type="button" className="btn btn-secondary" onClick={props.onCancel}>
        {ADMIN_CANCEL}
      </button>
    </div>
  );
}

export function UsersTab() {
  const queryClient = useQueryClient();
  const users = useQuery({ queryKey: queryKeys.adminUsers(), queryFn: api.listUsers });
  const [confirming, setConfirming] = useState<User | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const update = useMutation({
    mutationFn: (p: { user: User; patch: UserUpdate }) => api.updateUser(p.user.id, p.patch),
    onSuccess: (u) => {
      setError(null);
      setStatus(adminUserUpdated(u.email));
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminUsers() });
    },
    onError: (e) => {
      setStatus("");
      setError(formErrorsFrom(e, []).form);
    },
  });

  const tz = users.data?.meta.facility_tz ?? "UTC";
  const asOf = users.data?.meta.as_of ?? null;

  return (
    <div className="stack">
      <QueryState
        panel={ADMIN_USERS_PANEL}
        isPending={users.isPending}
        error={users.error}
        refetch={users.refetch}
      />
      <p aria-live="polite" className={styles.status}>
        {status}
      </p>
      <p role="alert" className={styles.formError}>
        {error}
      </p>
      {confirming && (
        <ConfirmDeactivate
          user={confirming}
          onCancel={() => setConfirming(null)}
          onConfirm={() => {
            update.mutate({ user: confirming, patch: { active: false } });
            setConfirming(null);
          }}
        />
      )}
      {users.data && users.data.items.length === 0 && (
        <p className="small muted">{ADMIN_USERS_EMPTY}</p>
      )}
      {users.data && users.data.items.length > 0 && (
        <div className="scroll-x">
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{ADMIN_USERS_COLUMNS.email}</th>
                <th scope="col">{ADMIN_USERS_COLUMNS.displayName}</th>
                <th scope="col">{ADMIN_USERS_COLUMNS.role}</th>
                <th scope="col">{ADMIN_USERS_COLUMNS.active}</th>
                <th scope="col">{ADMIN_USERS_COLUMNS.lastSignIn}</th>
                <th scope="col">
                  <span className="visually-hidden">{ADMIN_USERS_COLUMNS.actions}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {users.data.items.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.display_name}</td>
                  <td>
                    <select
                      className={styles.input}
                      aria-label={adminRoleFor(u.email)}
                      value={u.role}
                      onChange={(e) =>
                        update.mutate({ user: u, patch: { role: e.target.value as Role } })
                      }
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {ADMIN_ROLE_LABEL[r]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{u.active ? ADMIN_YES : ADMIN_NO}</td>
                  <td>
                    {u.last_login_at ? formatDateTimeShort(u.last_login_at, tz, asOf) : ADMIN_NEVER}
                  </td>
                  <td>
                    {u.active ? (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        aria-label={adminDeactivateName(u.email)}
                        onClick={() => setConfirming(u)}
                      >
                        {ADMIN_DEACTIVATE}
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        aria-label={adminReactivateName(u.email)}
                        onClick={() => update.mutate({ user: u, patch: { active: true } })}
                      >
                        {ADMIN_REACTIVATE}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <AddUserForm
        onAdded={(email) => {
          setError(null);
          setStatus(adminUserAdded(email));
        }}
      />
    </div>
  );
}
