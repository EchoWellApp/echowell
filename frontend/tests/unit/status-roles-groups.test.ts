// req: FE-207, FE-059, FE-102, UX-054
import { compressDeviceCodes, naturalCompare } from "@/lib/deviceGroups";
import { canReviewAlarms, canSeeStudyTeam, canWriteNotes, isAdmin } from "@/lib/roles";
import { toDisplayStatus } from "@/lib/status";
import { queryKeys } from "@/lib/queryKeys";

describe("toDisplayStatus (FE-207)", () => {
  it.each([
    ["alarm_on", false, "changed"],
    ["alarm_on", true, "changed"],
    ["no_alarm", true, "needs_attention"],
    ["baseline_forming", true, "needs_attention"],
    ["baseline_forming", false, "learning"],
    ["no_alarm", false, "usual"],
  ] as const)("%s + %s → %s", (status, flag, expected) => {
    expect(toDisplayStatus(status, flag)).toBe(expected);
  });
});

describe("roles (FE-059)", () => {
  it("gates notes, reviews, admin and the study team", () => {
    expect([
      canWriteNotes("admin"),
      canWriteNotes("clinician"),
      canWriteNotes("researcher"),
    ]).toEqual([true, true, false]);
    expect([
      canReviewAlarms("clinician"),
      canReviewAlarms("researcher"),
      canReviewAlarms(null),
    ]).toEqual([true, false, false]);
    expect([isAdmin("admin"), isAdmin("clinician")]).toEqual([true, false]);
    expect([
      canSeeStudyTeam("admin"),
      canSeeStudyTeam("researcher"),
      canSeeStudyTeam("clinician"),
    ]).toEqual([true, true, false]);
  });
});

describe("compressDeviceCodes (FE-102)", () => {
  it("joins runs of three or more", () => {
    expect(compressDeviceCodes(["D01", "D04", "D05", "D06", "D08", "D09", "D10"])).toBe(
      "D01, D04 to D06, D08 to D10",
    );
    expect(compressDeviceCodes(["D01", "D02"])).toBe("D01, D02");
    expect(compressDeviceCodes(["D07B", "D06", "D07", "D08"])).toBe("D06, D07, D07B, D08");
  });

  it("sorts naturally", () => {
    expect(["D10", "D2", "D07B", "D07"].sort(naturalCompare)).toEqual(["D2", "D07", "D07B", "D10"]);
  });
});

describe("queryKeys", () => {
  it("builds the keys of TRD 04 §4.7", () => {
    expect(queryKeys.scores("R09")).toEqual(["resident", "R09", "scores", null]);
    expect(queryKeys.alerts({ status: "open" })).toEqual([
      "alerts",
      { status: "open", residentCode: null },
    ]);
    expect(queryKeys.dataAlerts("open")).toEqual(["data-alerts", { status: "open" }]);
  });
});
