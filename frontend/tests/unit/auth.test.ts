// req: FE-050, FE-051, FE-052, FE-053, FE-057
import {
  clearToken,
  getExp,
  getToken,
  readExp,
  restoreToken,
  safeNext,
  setToken,
} from "@/lib/auth";
import { fakeJwt } from "../msw/handlers";

describe("auth token store", () => {
  afterEach(() => clearToken());

  it("reads exp from the JWT payload", () => {
    expect(readExp(fakeJwt(1_900_000_000))).toBe(1_900_000_000);
    expect(readExp("not-a-jwt")).toBeNull();
    expect(readExp("a.%%%.c")).toBeNull();
  });

  it("stores in memory and mirrors to sessionStorage only", () => {
    const token = fakeJwt();
    setToken(token);
    expect(getToken()).toBe(token);
    expect(JSON.parse(sessionStorage.getItem("echowell.auth") ?? "{}").token).toBe(token);
    expect(localStorage.length).toBe(0);
    expect(document.cookie).toBe("");
    clearToken();
    expect(getToken()).toBeNull();
    expect(sessionStorage.getItem("echowell.auth")).toBeNull();
  });

  it("refuses a token without exp", () => {
    expect(setToken("a.b.c")).toBeNull();
  });

  it("restores only when exp is more than 30 s away (FE-053)", () => {
    const now = Date.now();
    sessionStorage.setItem(
      "echowell.auth",
      JSON.stringify({ token: "t", exp: Math.floor(now / 1000) + 20 }),
    );
    expect(restoreToken(now)).toBeNull();
    expect(sessionStorage.getItem("echowell.auth")).toBeNull();
    sessionStorage.setItem(
      "echowell.auth",
      JSON.stringify({ token: "t", exp: Math.floor(now / 1000) + 120 }),
    );
    expect(restoreToken(now)?.token).toBe("t");
    expect(getExp()).toBe(Math.floor(now / 1000) + 120);
  });

  it("drops a corrupt stored value", () => {
    sessionStorage.setItem("echowell.auth", "{oops");
    expect(restoreToken()).toBeNull();
  });

  it("falls back to memory when sessionStorage throws", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const token = fakeJwt();
    expect(setToken(token)?.token).toBe(token);
    expect(getToken()).toBe(token);
    spy.mockRestore();
  });

  it("accepts only same-origin next paths (FE-057)", () => {
    expect(safeNext("/residents/R09")).toBe("/residents/R09");
    expect(safeNext("//evil.example")).toBe("/residents");
    expect(safeNext("https://evil.example")).toBe("/residents");
    expect(safeNext("/x?u=https://evil")).toBe("/residents");
    expect(safeNext(null)).toBe("/residents");
    expect(safeNext("/login")).toBe("/residents");
  });
});
