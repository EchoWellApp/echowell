"""
EchoWell pipeline test dataset generator, v0.1
Builds a 10-resident, 30-day synthetic test set in which every resident tests one
specific error mode, plus an expected-results answer key computed from the stated
rules. Run: python generate_pipeline_test_v0_1.py
"""
import numpy as np, pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import sys
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20261004
rng = np.random.default_rng(SEED)

# ---------------- test parameters (the rules the answer key assumes) ----------------
P = dict(
    facility_tz="America/Chicago", start_date="2026-10-01", n_days=30,
    usual_window_local="14:00 to 15:00", morning_window_local="09:00 to 10:00",
    morning_rule="local hour before 12:00",
    noise_limit_dbfs=-40.0, min_speech_s=1.0,
    baseline_n=16, screen_min_n=5, screen_f0_z=4.0, screen_other_z=3.0, screen_other_count=2,
    mad_scale=1.4826, pause_floor=0.5, composite_floor=0.1,
    cusum_k=0.5, cusum_h=5.0, offset_min_each=3,
)
TZ = ZoneInfo(P["facility_tz"]); UTC = ZoneInfo("UTC")

# name, unit, lo, hi, cv (None = absolute sd), abs_sd, decimals, composite direction (0 = not in composite), literature note
FEATS = [
 ("loudness_dbfs","dBFS",-30,-18,None,2.8,2,-1,"Down with depression; strongest"),
 ("total_phrase_duration_s","s",2.0,4.0,0.06,None,2,+1,"Up with depression"),
 ("speech_rate_syl_per_s","syllables/s",3.0,4.5,0.04,None,2,-1,"Down with depression"),
 ("articulation_rate_syl_per_s","syllables/s",4.0,5.5,0.04,None,2,-1,"Down with depression"),
 ("number_of_pauses","count",0.8,2.0,None,0.7,0,+1,"Up with depression"),
 ("pause_fraction","proportion",0.05,0.25,0.15,None,3,+1,"Up with depression"),
 ("voiced_fraction","proportion",0.50,0.75,0.05,None,3,-1,"Down with depression (moderate)"),
 ("mean_f0_hz","Hz",None,None,0.04,None,1,0,"Unsettled; sex-specific range"),
 ("f0_variability_st","semitones",2.0,4.5,0.08,None,2,0,"No consistent direction"),
 ("jitter_local_pct","percent",0.2,1.0,0.25,None,3,0,"No consistent direction"),
 ("shimmer_local_pct","percent",2.0,6.0,0.25,None,2,0,"No consistent direction"),
 ("hnr_db","dB",10,20,0.06,None,2,0,"No consistent direction"),
 ("cpps_db","dB",8,16,0.06,None,2,0,"Down where found; weak, not in composite"),
 ("alpha_ratio_db","dB",-20,0,None,1.5,2,0,"Down where found; weak, not in composite"),
 ("hammarberg_index_db","dB",15,30,0.06,None,2,0,"Down where found; weak, not in composite"),
 ("mfcc1","unitless",20,40,None,2.0,2,0,"Mixed; placeholder range"),
 ("mfcc2","unitless",0,15,None,1.5,2,0,"Mixed; placeholder range"),
 ("mfcc3","unitless",-5,10,None,1.5,2,0,"Mixed; placeholder range"),
 ("mfcc4","unitless",-10,5,None,1.5,2,0,"Mixed; placeholder range"),
]
FN = [f[0] for f in FEATS]; FD = {f[0]: f for f in FEATS}
COMP = [f[0] for f in FEATS if f[7] != 0]; DIR = {f[0]: f[7] for f in FEATS}
F0RANGE = {"F": (165, 200), "M": (110, 145)}

RESIDENTS = [  # id, sex, device, test case name, one-line focus
 ("R01","F","D01","Clean control","No faults at all; checks median, MAD and that no alarm rings"),
 ("R02","M","D02","Missing days","Days with no record must be logged as missing, never filled in; shares device D02 with R03"),
 ("R03","F","D02","Set-aside sessions","Noisy, quality-flagged, too-short and combined-fault sessions must be set aside with the right reasons"),
 ("R04","M","D04","Duplicate records","The same session sent twice, once out of order, must be kept once"),
 ("R05","F","D05","Possible other speaker","Sessions that look like a different person must be quarantined, before and after the baseline exists"),
 ("R06","M","D06","Morning effect","Morning sessions carry a planted offset that the pipeline must estimate and remove"),
 ("R07","F","D07","Device move","Move to a new device on day 13 must start a new epoch and a fresh baseline, with no alarm"),
 ("R08","M","D08","Too few sessions","Low adherence leaves fewer than 16 usable sessions, so no baseline and no scores"),
 ("R09","F","D09","Step change","Sudden 1.5 SD shift toward depression from day 21 must ring the alarm"),
 ("R10","M","D10","Gradual drift","Slow drift toward depression from day 17 must ring the alarm, and the frozen baseline must not follow it"),
]
SEX = {r[0]: r[1] for r in RESIDENTS}

MORNING_OFFSET = {"loudness_dbfs": -1.5, "total_phrase_duration_s": 0.10, "speech_rate_syl_per_s": -0.12,
                  "articulation_rate_syl_per_s": -0.10, "pause_fraction": 0.010, "voiced_fraction": -0.020}
DEVICE_EFFECT = {"loudness_dbfs": 3.0, "hnr_db": 1.5, "alpha_ratio_db": 2.0}

def draw_means(sex):
    m = {}
    for n,u,lo,hi,cv,asd,dec,d,_ in FEATS:
        if n == "mean_f0_hz": lo,hi = F0RANGE[sex]
        m[n] = rng.uniform(lo,hi)
    return m
def sd_of(n, mean):
    f = FD[n]; return f[5] if f[4] is None else f[4]*abs(mean)

def make_values(means, shift_sd=0.0, extra=None):
    u = rng.normal(); v = {}
    for n in FN:
        sd = sd_of(n, means[n]); e = rng.normal()
        if n in COMP:
            x = means[n] + sd*(0.6*u*DIR[n] + 0.8*e) + shift_sd*sd*DIR[n]
        else:
            x = means[n] + sd*e
        if extra and n in extra: x += extra[n]
        v[n] = x
    return v

def finish(v):
    out = {}
    for n in FN:
        x = v[n]; dec = FD[n][6]
        if n == "number_of_pauses": x = max(0, int(round(x)))
        if n in ("pause_fraction","voiced_fraction"): x = min(max(x,0.0),1.0)
        if n == "jitter_local_pct": x = max(x, 0.05)
        if n == "shimmer_local_pct": x = max(x, 0.5)
        out[n] = round(x, dec) if dec else x
    return out

start = datetime.fromisoformat(P["start_date"])
records = []   # every record that ARRIVES (incl. duplicates)
placeholders = []  # resident-days with no record
notes = {}     # (resident, day) -> (error mode text, planted)

def add(rid, dev, day, vals, morning=False, noise=None, flag="ok", speech=None, note=None,
        fw="fw-1.0.0", sw="openSMILE 3.0.2"):
    hr = 9 if morning else 14
    local = datetime(start.year, start.month, start.day, hr, int(rng.integers(0,60)), int(rng.integers(0,60)), tzinfo=TZ) + timedelta(days=day-1)
    rec = dict(schema_version="0.1", session_id=f"{rid}-{local:%Y%m%d}-01", resident_id=rid, device_id=dev,
               timestamp_utc=local.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
               mic_noise_level_dbfs=round(noise if noise is not None else rng.uniform(-56,-46),1),
               audio_quality_flag=flag, extraction_software_version=sw, device_firmware_version=fw,
               phrase_id="P01")
    rec["speech_duration_s"] = speech if speech is not None else vals["total_phrase_duration_s"]
    rec.update(vals); rec["_day"] = day; rec["_note"] = note; rec["_local"] = local
    records.append(rec); return rec

def miss(rid, dev, day, note):
    placeholders.append(dict(resident_id=rid, device_id=dev, _day=day, _note=note))

for rid, sex, dev, case, focus in RESIDENTS:
    means = draw_means(sex)
    for day in range(1, 31):
        if rid == "R01":
            add(rid, dev, day, finish(make_values(means)), note="No fault. Clean control session")
        elif rid == "R02":
            if day == 12: miss(rid, dev, day, "No record from either resident on shared device D02 this day. Must be logged as a device gap, not as R02 skipping"); continue
            if day in (4, 9, 10, 17, 23): miss(rid, dev, day, "No record received. Must be logged as missing (resident), not filled in or carried forward"); continue
            add(rid, dev, day, finish(make_values(means)), note="No fault. Background session for the missing-days test")
        elif rid == "R03":
            if day == 12: miss(rid, dev, day, "No record from either resident on shared device D02 this day. Must be logged as a device gap, not as R03 skipping"); continue
            v = make_values(means)
            if day in (3, 14):
                v["hnr_db"] -= 4; v["jitter_local_pct"] *= 1.6; v["shimmer_local_pct"] *= 1.5
                add(rid, dev, day, finish(v), noise=-32.0, note="Mic noise -32 dBFS is above the -40 dBFS limit, quality flag still ok, features degraded. Tests the noise check on its own")
            elif day in (7, 22):
                add(rid, dev, day, finish(v), flag="poor", note="Device quality flag is poor while noise level is normal. Tests that the quality flag is honoured on its own")
            elif day in (10, 26):
                fv = finish(v); fv["total_phrase_duration_s"] = 0.62
                add(rid, dev, day, fv, speech=0.62, note="Speech duration 0.62 s is below the 1.0 s minimum (phrase cut off). Tests the short-speech check")
            elif day == 18:
                v["hnr_db"] -= 4; v["jitter_local_pct"] *= 1.6
                add(rid, dev, day, finish(v), noise=-30.0, flag="poor", note="Two faults at once: noise above limit and quality flag poor. Both reasons must be recorded")
            else:
                add(rid, dev, day, finish(make_values(means) if False else v), note="No fault. Background session for the set-aside test")
        elif rid == "R04":
            r = add(rid, dev, day, finish(make_values(means)), note="No fault. Background session for the duplicate test")
            if day == 5:
                d = dict(r); d["_note"] = "DUPLICATE: identical copy of day 5 session sent again immediately. Must be dropped and logged, first copy kept"; d["_dup"] = "adjacent"; records.append(d)
            if day == 18:
                d = dict(r); d["_note"] = "DUPLICATE: identical copy of day 18 session arriving at the end of the file, out of order. Must be dropped and logged, first copy kept"; d["_dup"] = "late"
        elif rid == "R05":
            if day in (8, 22):
                other = draw_means(sex)
                v = make_values(means)
                v["mean_f0_hz"] = rng.uniform(*F0RANGE["M"])
                for n, k in (("speech_rate_syl_per_s", 4.5), ("articulation_rate_syl_per_s", 4.5), ("total_phrase_duration_s", -4.5)):
                    v[n] = means[n] + k*sd_of(n, means[n])
                when = "before the baseline is frozen (screened against the provisional median of prior sessions)" if day == 8 else "after the baseline is frozen"
                add(rid, dev, day, finish(v), note=f"POSSIBLE OTHER SPEAKER: male-range F0 and much faster, shorter speech than this resident, {when}. Must be quarantined, not scored, not used in the baseline")
            else:
                add(rid, dev, day, finish(make_values(means)), note="No fault. Background session for the other-speaker test")
        elif rid == "R06":
            morning = (day % 3 == 1)
            extra = MORNING_OFFSET if morning else None
            add(rid, dev, day, finish(make_values(means, extra=extra)), morning=morning,
                note=("MORNING SESSION (09:00 local, 14:xx UTC) carrying the morning effect: loudness -1.5 dB, phrase duration +0.10 s, speech rate -0.12, articulation rate -0.10, pause fraction +0.010, voiced fraction -0.020. Pipeline must classify it as morning from LOCAL time and subtract the configured offset for each feature"
                      if morning else "Usual-window session (14:00 local, 19:xx UTC). Not morning, so no offset is applied"))
        elif rid == "R07":
            if day < 13:
                add(rid, "D07", day, finish(make_values(means)), note="Epoch 1 on device D07. Only 12 sessions, so no baseline forms before the move")
            else:
                add(rid, "D07B", day, finish(make_values(means, extra=DEVICE_EFFECT)),
                    note=("FIRST SESSION ON NEW DEVICE D07B: microphone adds loudness +3.0 dB, HNR +1.5 dB, alpha ratio +2.0 dB. Must open epoch 2; the 12 epoch 1 sessions must NOT count toward the new baseline" if day == 13
                          else "Epoch 2 on device D07B (device effect present). Counts toward the epoch 2 baseline"))
        elif rid == "R08":
            if day in (2,4,6,8,11,13,15,17,19,21,24,27): miss(rid, dev, day, "No record received (low adherence). Must be logged as missing (resident)"); continue
            v = make_values(means)
            if day in (5, 20):
                v["hnr_db"] -= 4; add(rid, dev, day, finish(v), noise=-33.0, note="Mic noise above limit. Set aside, which pushes usable sessions below the baseline minimum")
            elif day in (9, 25):
                add(rid, dev, day, finish(v), flag="poor", note="Quality flag poor. Set aside, which pushes usable sessions below the baseline minimum")
            elif day == 29:
                fv = finish(v); fv["total_phrase_duration_s"] = 0.58
                add(rid, dev, day, fv, speech=0.58, note="Speech too short. Set aside")
            else:
                add(rid, dev, day, finish(v), note="No fault. Usable, but too few such sessions exist to form a baseline")
        elif rid == "R09":
            shift = 1.5 if day >= 21 else 0.0
            add(rid, dev, day, finish(make_values(means, shift_sd=shift)),
                note=("STEP CHANGE: all seven composite features shifted 1.5 within-person SD toward depression from today (true onset). Alarm should ring within a few sessions" if day == 21
                      else "Step change continues (1.5 SD toward depression)" if day > 21 else "No fault. Before the inserted change"))
        elif rid == "R10":
            shift = 2.0*(day-16)/14 if day >= 17 else 0.0
            add(rid, dev, day, finish(make_values(means, shift_sd=shift)),
                note=(f"GRADUAL DRIFT: composite features drifting toward depression, now {shift:.2f} SD (true onset day 17, reaches 2.0 SD on day 30). Baseline must stay frozen"
                      if day >= 17 else "No fault. Before the inserted drift"))

# late duplicate goes to the end of the arrival order
late = [r for r in records if r["resident_id"]=="R04" and r["_day"]==18][0]
d = dict(late); d["_note"] = "DUPLICATE: identical copy of day 18 session arriving at the end of the file, out of order. Must be dropped and logged, first copy kept"; d["_dup"]="late"
records.append(d)
for i, r in enumerate(records): r["_arrival"] = i + 1

# ---------------- expected results, computed from the stated rules ----------------
seen = set()
for r in records:
    if r["session_id"] in seen:
        r["_status"], r["_reason"] = "duplicate", "session_id already received"; continue
    seen.add(r["session_id"])
    reasons = []
    if r["audio_quality_flag"] != "ok": reasons.append("quality flag poor")
    if r["mic_noise_level_dbfs"] > P["noise_limit_dbfs"]: reasons.append("noise above limit")
    if r["speech_duration_s"] < P["min_speech_s"]: reasons.append("speech too short")
    if reasons: r["_status"], r["_reason"] = "set_aside", "; ".join(reasons)
    else: r["_status"], r["_reason"] = "pending_screen", ""

def epoch_key(r): return (r["device_id"], r["device_firmware_version"], r["extraction_software_version"])
def robust(vals, floor=0.0):
    a = np.array(vals, float); med = float(np.median(a)); mad = float(np.median(np.abs(a-med)))
    return med, mad, max(mad*P["mad_scale"], floor)
def floor_of(n): return P["pause_floor"] if n == "number_of_pauses" else 0.0

# speaker screen (raw values, time order, per resident and epoch)
by_res = {}
for r in records:
    if r["_status"] == "duplicate": continue
    by_res.setdefault(r["resident_id"], []).append(r)
for rid, rs in by_res.items():
    rs.sort(key=lambda r: r["timestamp_utc"])
    ep, prior = None, []
    epn = 0
    for r in rs:
        if epoch_key(r) != ep: ep, prior, epn = epoch_key(r), [], epn + 1
        r["_epoch"] = epn
        if r["_status"] != "pending_screen": continue
        ref = prior[:P["baseline_n"]]
        if len(ref) >= P["screen_min_n"]:
            z = {}
            for n in ["mean_f0_hz"] + COMP:
                med, mad, sp = robust([p[n] for p in ref], floor_of(n))
                z[n] = (r[n]-med)/sp if sp > 0 else 0.0
            others = sum(abs(z[n]) >= P["screen_other_z"] for n in COMP)
            r["_screen"] = f"F0 z={z['mean_f0_hz']:.2f}; composite features with |z|>=3: {others}"
            if abs(z["mean_f0_hz"]) >= P["screen_f0_z"] and others >= P["screen_other_count"]:
                r["_status"], r["_reason"] = "quarantined", "possible other speaker (" + r["_screen"] + ")"; continue
        r["_status"] = "usable"; prior.append(r)

usable = [r for r in records if r.get("_status") == "usable"]
def is_morning(r): return r["_local"].hour < 12
for r in records: r["_morning"] = is_morning(r)

# baseline membership (first N usable per resident-epoch)
groups = {}
for r in sorted(usable, key=lambda r: r["timestamp_utc"]):
    groups.setdefault((r["resident_id"], r["_epoch"]), []).append(r)
for k, rs in groups.items():
    for i, r in enumerate(rs): r["_ord"] = i + 1; r["_inbase"] = i < P["baseline_n"]

# morning offset: configured per feature (P["morning_offset"]), applied to morning sessions only
OFF = {n: MORNING_OFFSET.get(n, 0.0) for n in FN}
qual = []
for r in records:
    for n in FN:
        if n in r: r["_adj_"+n] = r[n] - (OFF[n] if r["_morning"] else 0.0)

# baselines, scores, CUSUM
base_rows, score_rows, summary = [], [], {}
for (rid, epn), rs in sorted(groups.items()):
    b = [r for r in rs if r["_inbase"]]
    info = dict(resident_id=rid, epoch=epn, device_id=rs[0]["device_id"], usable_in_epoch=len(rs))
    if len(b) < P["baseline_n"]:
        summary.setdefault(rid, []).append(dict(info, baseline_formed="no")); continue
    BL = {}
    for n in FN:
        med, mad, sp = robust([r["_adj_"+n] for r in b], floor_of(n)); BL[n] = (med, mad, sp)
        base_rows.append(dict(resident_id=rid, epoch=epn, device_id=rs[0]["device_id"], feature=n,
                              n_sessions=len(b), first_session=b[0]["session_id"], baseline_frozen_after=b[-1]["session_id"],
                              median=med, mad=mad, robust_spread=sp, floor_applied="yes" if sp > mad*P["mad_scale"] else "no"))
    def comp_raw(r): return float(np.mean([DIR[n]*(r["_adj_"+n]-BL[n][0])/BL[n][2] for n in COMP]))
    cm, cmad, csp = robust([comp_raw(r) for r in b], P["composite_floor"])
    base_rows.append(dict(resident_id=rid, epoch=epn, device_id=rs[0]["device_id"], feature="COMPOSITE (raw signed mean of 7 z)",
                          n_sessions=len(b), first_session=b[0]["session_id"], baseline_frozen_after=b[-1]["session_id"],
                          median=cm, mad=cmad, robust_spread=csp, floor_applied="yes" if csp > cmad*P["mad_scale"] else "no"))
    S, flagged = 0.0, None
    for r in rs:
        if r["_inbase"]: continue
        zr = {n: (r["_adj_"+n]-BL[n][0])/BL[n][2] for n in COMP}
        craw = comp_raw(r); cz = (craw-cm)/csp
        S = max(0.0, S + cz - P["cusum_k"])
        newflag = flagged is None and S >= P["cusum_h"]
        if newflag: flagged = r["session_id"]
        row = dict(session_id=r["session_id"], resident_id=rid, epoch=epn, local_date=r["_local"].strftime("%Y-%m-%d"), morning=r["_morning"])
        for n in COMP: row["z_"+n] = zr[n]
        row.update(composite_raw=craw, composite_z=cz, cusum_tally=S, alarm=("RINGS (first crossing)" if newflag else ("on" if flagged else "off")))
        score_rows.append(row)
    summary.setdefault(rid, []).append(dict(info, baseline_formed="yes", baseline_frozen_after=b[-1]["session_id"],
                                            scored_sessions=len(rs)-len(b), first_alarm_session=flagged or "none"))

# ---------------- write outputs ----------------
import sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
fields = ["schema_version","session_id","resident_id","device_id","timestamp_utc","mic_noise_level_dbfs","audio_quality_flag",
          "extraction_software_version","device_firmware_version","speech_duration_s","phrase_id"] + FN
pd.DataFrame([{k: r[k] for k in fields} for r in records]).to_csv(f"{OUT}/EchoWell_pipeline_test_input_v0_1.csv", index=False)

rows = []
for r in records:
    d = dict(_sort=(r["resident_id"], r["_day"], r.get("_dup","")), resident_id=r["resident_id"], test_case=dict((x[0],x[3]) for x in RESIDENTS)[r["resident_id"]],
                     day=r["_day"], local_time=r["_local"].strftime("%Y-%m-%d %H:%M"), arrival_order=r["_arrival"],
                     error_mode_tested=r["_note"], expected_status=r["_status"], expected_reason=r["_reason"],
                     expected_morning=("yes" if r["_morning"] else "no"), expected_epoch=r.get("_epoch",""),
                     in_baseline=("yes" if r.get("_inbase") else "no"))
    d.update({k: r[k] for k in fields if k != "resident_id"}); rows.append(d)
for p in placeholders:
    rows.append(dict(_sort=(p["resident_id"], p["_day"], ""), resident_id=p["resident_id"], test_case=dict((x[0],x[3]) for x in RESIDENTS)[p["resident_id"]],
                     day=p["_day"], local_time=(start+timedelta(days=p["_day"]-1)).strftime("%Y-%m-%d"), arrival_order="no record",
                     error_mode_tested=p["_note"],
                     expected_status=("missing_device_gap" if "device gap" in p["_note"] else "missing_resident"),
                     expected_reason=("all residents on shared device D02 have no record" if "device gap" in p["_note"] else "no record received"),
                     expected_morning="", expected_epoch="", in_baseline="no", device_id=p["device_id"]))
ann = pd.DataFrame(rows).sort_values("_sort").drop(columns=["_sort"])

stat = ann.groupby(["resident_id","expected_status"]).size().unstack(fill_value=0).reset_index()
summ = []
for rid, *_ in RESIDENTS:
    for s in summary.get(rid, [dict(resident_id=rid, epoch=1, baseline_formed="no")]):
        summ.append(s)
off = pd.DataFrame([dict(feature=n, unit=FD[n][1], configured_morning_offset=OFF[n],
                         how_applied=("adjusted value = raw value minus this offset, morning sessions only" if OFF[n] else "zero: morning and later sessions treated alike")) for n in FN])
pd.to_pickle(dict(P=P, FEATS=FEATS, RES=RESIDENTS, ann=ann, stat=stat, summ=pd.DataFrame(summ), off=off,
                  base=pd.DataFrame(base_rows), scores=pd.DataFrame(score_rows), qual=[q[0] for q in qual]), f"{OUT}/_bundle.pkl")

# ---------------- workbook ----------------
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
b = pd.read_pickle(f"{OUT}/_bundle.pkl"); P=b["P"]; FEATS=b["FEATS"]; RES=b["RES"]
summ=b["summ"]; ann=b["ann"]

F = "Arial"; H = Font(name=F, bold=True, color="FFFFFF"); N = Font(name=F, size=10)
HF = PatternFill("solid", fgColor="1F4E78"); DESC = PatternFill("solid", fgColor="FFF2CC")
wb = Workbook(); ws0 = wb.active

def table(ws, df, widths=None, desc_cols=(), numfmt=None, wrap_cols=()):
    cols = list(df.columns)
    for j,c in enumerate(cols,1):
        cell = ws.cell(row=1,column=j,value=c); cell.font=H; cell.fill=HF
        cell.alignment=Alignment(wrap_text=True, vertical="top")
    for i,row in enumerate(df.itertuples(index=False),2):
        for j,v in enumerate(row,1):
            if isinstance(v,float) and pd.isna(v): v=""
            cell=ws.cell(row=i,column=j,value=v); cell.font=N
            if cols[j-1] in desc_cols: cell.fill=DESC
            if cols[j-1] in wrap_cols or cols[j-1] in desc_cols: cell.alignment=Alignment(wrap_text=True, vertical="top")
            if numfmt and cols[j-1] in numfmt and isinstance(v,(int,float)): cell.number_format=numfmt[cols[j-1]]
    for j,c in enumerate(cols,1):
        w = (widths or {}).get(c, max(10, min(28, len(c)+2)))
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "B2"; ws.auto_filter.ref = ws.dimensions

# ---- README
ws0.title = "README"
outcome = {r.resident_id: r for r in summ.itertuples()}
lines = [
("EchoWell pipeline test set, v0.1", "title"),
("Generated 7 October 2026 for Team 2 (cloud storage and processing). Synthetic data only: 10 residents, 30 days, one session per day.", ""),
("", ""),
("What this is for", "h"),
("Each resident tests one specific error mode, so a wrong result points straight at the step that broke. Every expected result in this workbook was computed from the rules on the Parameters sheet, independently of your pipeline. Run the pipeline on the input CSV, then compare its output to the Exp_ sheets.", ""),
("", ""),
("Files", "h"),
("EchoWell_pipeline_test_input_v0_1.csv: the only file the pipeline reads. Device fields only, in arrival order, no descriptions or answers. Missing days are simply absent, as they would be in real data.", ""),
("This workbook: the test plan, the annotated sessions (with the error mode each row tests) and the expected results. Treat it like the answer key: keep it out of the pipeline's input folder.", ""),
("generate_pipeline_test_v0_1.py: rebuilds everything from scratch (seed 20261004), so the expected results can be audited or regenerated.", ""),
("", ""),
("Sheets", "h"),
("Parameters: every rule and threshold the expected results assume. Change one and the answers change; rerun the script.", ""),
("Test_plan: one row per resident: the error mode it tests and the correct outcome.", ""),
("Data_dictionary: fields, units, plausible ranges, direction with depression, and whether each feature enters the composite.", ""),
("Annotated_sessions: every resident-day, including days with no record and the duplicate copies. Yellow columns describe the error mode tested and the expected handling.", ""),
("Exp_status_counts: expected count of each session status per resident.", ""),
("Exp_resident_outcomes: whether a baseline forms, when it freezes, how many sessions are scored, and when the alarm first rings.", ""),
("Exp_baselines: expected median, MAD and robust spread per resident, epoch and feature (after the morning adjustment).", ""),
("Exp_morning_offset: the offset subtracted from each feature for morning sessions.", ""),
("Exp_scores: expected z scores, composite, CUSUM tally and alarm state for every scored session.", ""),
("", ""),
("Read before using", "h"),
("1. Column names are placeholders. Team 1 has not yet confirmed extractor output names, so features use readable names with units, following the feature table in the Team 1 dataset specification (section 4). Rename the columns once Team 1 confirms; the values and tests still hold.", ""),
("2. Test-only baseline length. The baseline here freezes after 16 usable sessions, not 30, so that a 30-day test can reach the scoring and alarm steps. 16 is even on purpose: the median of an even count is the average of the two middle values, a common place for median code to go wrong.", ""),
("3. The morning offset is configured, not estimated. One resident with about 6 morning sessions in its baseline cannot reliably estimate an effect this small; in trial runs the estimate missed the true loudness offset by almost double and produced sizable fake offsets for features with no true effect. So this test checks the two things that must be exactly right: classifying morning from LOCAL time (timestamps arrive in UTC), and subtracting the configured offset. Estimating the offset belongs in the later test on Team 1's 50-resident, 120-day dataset.", ""),
("4. Facility time zone is assumed to be America/Chicago (UTC minus 5 in October, no daylight saving change inside the test window). Change it on the Parameters sheet if the facility is elsewhere.", ""),
("5. Alarms here test arithmetic, not detection performance. The fixture seed was chosen so the eight residents with no inserted change do not alarm. Across 100 other seeds, 10% of those no-change residents raised a false alarm within 14 scored sessions using a 16-session baseline. That is far above what the textbook CUSUM settings promise, and is a concrete reason the real baseline should be about 30 sessions and the limit calibrated on Team 1's larger dataset.", ""),
("6. The pause-count floor is exercised. Number of pauses is a small whole number, so its MAD is 0 for most residents. The 0.5 floor on its spread prevents dividing by zero; Exp_baselines marks every row where the floor was applied.", ""),
]
ws0.column_dimensions["A"].width = 120
for i,(t,k) in enumerate(lines,1):
    c=ws0.cell(row=i,column=1,value=t); c.alignment=Alignment(wrap_text=True, vertical="top")
    c.font = Font(name=F, bold=True, size=14) if k=="title" else Font(name=F, bold=True, size=11) if k=="h" else Font(name=F, size=10)

# ---- Parameters
prm = [
("facility_tz", P["facility_tz"], "Time zone used to turn UTC timestamps into local time (assumption)"),
("usual session window", P["usual_window_local"]+" local", "Everyone except R06's morning days"),
("morning rule", P["morning_rule"], "A session is morning if its LOCAL hour is before 12"),
("noise limit", P["noise_limit_dbfs"], "Set aside if mic_noise_level_dbfs is above this (dBFS)"),
("minimum speech duration", P["min_speech_s"], "Set aside if speech_duration_s is below this (seconds)"),
("quality flag", "ok / poor", "Set aside if audio_quality_flag is poor"),
("duplicate rule", "same session_id", "Second and later copies are duplicates; the first arrival is kept"),
("set-aside reasons", "all that apply", "Listed in the order: quality flag, noise, speech duration, separated by semicolons"),
("missing_resident", "no record that local day", "A resident-day with no record at all"),
("missing_device_gap", "shared device, all residents silent", "No record from ANY resident on a device that serves 2 or more residents, on the same day"),
("epoch keys", "device_id + firmware + software version", "Any change in these starts a new epoch; the baseline count restarts from zero"),
("baseline length (test only)", P["baseline_n"], "Baseline = first 16 usable sessions in the epoch (time order), then frozen. Real use: about 30"),
("baseline values", "morning-adjusted", "Baseline and scores use adjusted values; the speaker screen uses raw values"),
("baseline centre", "median", ""),
("baseline spread", f"MAD x {P['mad_scale']}", "MAD = median absolute deviation from the median"),
("spread floor, number_of_pauses", P["pause_floor"], "Spread is never below this, to avoid dividing by zero"),
("speaker screen reference", f"raw median and spread of up to the first {P['baseline_n']} prior usable sessions in the epoch", f"Screen runs only once at least {P['screen_min_n']} prior usable sessions exist"),
("speaker screen rule", f"|F0 z| >= {P['screen_f0_z']} AND at least {P['screen_other_count']} composite features with |z| >= {P['screen_other_z']}", "Quarantined sessions are not scored and never enter the baseline"),
("morning offset", "see Exp_morning_offset", "Adjusted value = raw value minus offset, morning sessions only"),
("z score", "(adjusted value - baseline median) / baseline spread", ""),
("composite features and signs", "loudness -1, phrase duration +1, speech rate -1, articulation rate -1, pauses +1, pause fraction +1, voiced fraction -1", "Signed z = sign x z, so positive always means toward depression"),
("composite raw", "mean of the 7 signed z", ""),
("composite z", "(composite raw - its baseline median) / its baseline spread", f"Composite spread floor {P['composite_floor']}"),
("CUSUM", f"tally = max(0, previous tally + composite z - {P['cusum_k']})", "Starts at 0 with the first session after the baseline freezes. Set-aside, quarantined and missing days do not update it"),
("alarm", f"tally >= {P['cusum_h']}", "First crossing is the alarm; it stays on (no clinician review is simulated)"),
]
ws=wb.create_sheet("Parameters")
table(ws, pd.DataFrame(prm, columns=["parameter","value","meaning"]), widths={"parameter":32,"value":60,"meaning":80}, wrap_cols=("value","meaning"))

# ---- Test plan
o = lambda rid: summ[summ.resident_id==rid]
def first_alarm(rid):
    s=o(rid); v=[x for x in s.first_alarm_session if isinstance(x,str) and x!="none"]; return v[0] if v else "none"
exp_out = {
"R01":"All 30 sessions usable. Baseline freezes after R01-20261016-01. Medians and MADs match Exp_baselines. 14 sessions scored, no alarm.",
"R02":"24 usable. Days 4, 9, 10, 17, 23 logged missing_resident. Day 12 logged missing_device_gap (not R02's fault). Nothing filled in or carried forward. No alarm.",
"R03":"22 usable, 7 set aside with reasons: noise (days 3, 14), quality flag (7, 22), short speech (10, 26), both flag and noise (18). Day 12 missing_device_gap. No alarm.",
"R04":"30 unique sessions kept. 2 duplicates logged: day 5 (adjacent copy) and day 18 (copy arriving last in the file). Baseline and scores identical to a run without the copies.",
"R05":"Days 8 and 22 quarantined as possible other speaker; neither enters the baseline or the scores. Baseline freezes after R05-20261017-01 (one day later than R01, because day 8 is excluded). No alarm.",
"R06":"10 morning sessions (days 1, 4, 7 ... 28) classified as morning from local time; configured offset subtracted from 6 features. 20 later-window sessions untouched. No alarm.",
"R07":"Epoch 1 (D07, days 1 to 12): 12 sessions, no baseline. Epoch 2 (D07B, from day 13) starts from zero: baseline freezes after R07-20261028-01, 2 sessions scored, no alarm.",
"R08":"13 usable, 5 set aside, 12 missing_resident. Fewer than 16 usable, so no baseline and no scores; the pipeline must report baseline pending rather than error or score.",
"R09":f"Baseline freezes before the change (after R09-20261016-01). Alarm first rings at {first_alarm('R09')}, the true onset day.",
"R10":f"Baseline stays frozen at its day 16 values while values drift. Alarm first rings at {first_alarm('R10')}, on day 24, 7 days after the true onset on day 17.",
}
tp = pd.DataFrame([dict(resident_id=r[0], sex=r[1], device=("D07 then D07B" if r[0]=="R07" else r[2]), test_case=r[3],
                        error_mode_tested=r[4], correct_outcome=exp_out[r[0]]) for r in RES])
ws=wb.create_sheet("Test_plan")
table(ws, tp, widths={"resident_id":11,"sex":6,"device":14,"test_case":20,"error_mode_tested":60,"correct_outcome":80}, desc_cols=("error_mode_tested",), wrap_cols=("correct_outcome",))

# ---- Data dictionary
rec_fields = [
("schema_version","text","Data format version","0.1"),("session_id","text","Unique per session; used to drop duplicates","resident-date-01"),
("resident_id","text","Resident",""),("device_id","text","Recording device",""),
("timestamp_utc","YYYY-MM-DD HH:MM:SS","UTC; convert to local time before deciding morning",""),
("mic_noise_level_dbfs","dBFS","Background noise level","about -56 to -46 normal"),
("audio_quality_flag","ok / poor","Device's own usability flag",""),
("extraction_software_version","text","Feature extractor and version","openSMILE 3.0.2 (placeholder)"),
("device_firmware_version","text","Device firmware",""),("speech_duration_s","s","Length of detected speech",""),
("phrase_id","text","Which phrase was spoken","P01 throughout"),
]
dd = [dict(field=a, unit=u, description=d, plausible_range=r, direction_with_depression="", in_composite="", composite_sign="") for a,u,d,r in rec_fields]
for n,u,lo,hi,cv,asd,dec,d,note in FEATS:
    rng = "F 165 to 200, M 110 to 145" if n=="mean_f0_hz" else ("0 to 3 (whole numbers)" if n=="number_of_pauses" else f"{lo} to {hi}")
    dd.append(dict(field=n, unit=u, description="Acoustic feature (placeholder column name)", plausible_range=rng,
                   direction_with_depression=note, in_composite=("yes" if d else "no"), composite_sign=(d if d else "")))
ws=wb.create_sheet("Data_dictionary")
table(ws, pd.DataFrame(dd), widths={"field":30,"unit":20,"description":48,"plausible_range":26,"direction_with_depression":40,"in_composite":12,"composite_sign":14}, wrap_cols=("description",))

# ---- Annotated sessions
ws=wb.create_sheet("Annotated_sessions")
table(ws, ann, widths={"error_mode_tested":70,"expected_reason":34,"test_case":18,"local_time":16,"timestamp_utc":19,"session_id":18},
      desc_cols=("error_mode_tested","expected_status","expected_reason"))
ws.freeze_panes = "D2"

# ---- Expected sheets
st=b["stat"].copy(); st.columns.name=None
ws=wb.create_sheet("Exp_status_counts"); table(ws, st)
so = summ.copy()
so["note"] = so.apply(lambda r: "Too few usable sessions: baseline pending, nothing scored" if r.baseline_formed=="no" else "", axis=1)
ws=wb.create_sheet("Exp_resident_outcomes"); table(ws, so, widths={"note":50,"baseline_frozen_after":20,"first_alarm_session":20})
ws=wb.create_sheet("Exp_baselines"); table(ws, b["base"], widths={"feature":34,"first_session":18,"baseline_frozen_after":20},
      numfmt={"median":"0.0000","mad":"0.0000","robust_spread":"0.0000"})
ws=wb.create_sheet("Exp_morning_offset"); table(ws, b["off"], widths={"feature":30,"how_applied":64})
sc=b["scores"]; nf={c:"0.000" for c in sc.columns if c.startswith("z_") or c.startswith("composite") or c=="cusum_tally"}
ws=wb.create_sheet("Exp_scores"); table(ws, sc, numfmt=nf, widths={"alarm":22,"session_id":18})
wb.save(f"{OUT}/EchoWell_pipeline_test_v0_1.xlsx")
import os; os.remove(f"{OUT}/_bundle.pkl")
print("Wrote input CSV and workbook to", OUT)
