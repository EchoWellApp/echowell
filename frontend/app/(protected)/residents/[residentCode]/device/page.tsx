"use client";
// Chart section "Device" (TRD 11 §4.5.8, UX-430..UX-433; TRD 04 §4.6.2: getResident, getDevices,
// getCheckins). The banner, section nav and not-found state come from the chart layout (FE-206).
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { DevicePanel } from "@/components/DevicePanel/DevicePanel";
import { QueryState, SectionState } from "@/components/SectionState/SectionState";
import { useDocumentTitle } from "@/lib/hooks";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import { DEVICE_PANEL_NAME, DEVICE_SECTION, deviceNoneAssigned } from "@/lib/wording";
import * as api from "@/services/api";
import { ApiError } from "@/services/api";
import { codeParam, isValidResidentCode } from "../section";

export default function DeviceSectionPage() {
  const code = codeParam(useParams());
  const valid = isValidResidentCode(code);
  useDocumentTitle(`${code} · ${DEVICE_SECTION}`);

  const resident = useQuery({
    queryKey: queryKeys.resident(code),
    queryFn: () => api.getResident(code),
    refetchInterval: REFRESH_MS,
    enabled: valid,
  });
  const devices = useQuery({
    queryKey: queryKeys.devices(),
    queryFn: api.getDevices,
    refetchInterval: REFRESH_MS,
    enabled: valid,
  });
  const checkins = useQuery({
    queryKey: queryKeys.checkins(code),
    queryFn: () => api.getCheckins(code),
    refetchInterval: REFRESH_MS,
    enabled: valid,
  });

  if (!valid) return null;
  // The chart layout shows "Resident <code> was not found." (FE-142).
  if (resident.error instanceof ApiError && resident.error.status === 404) return null;

  if (resident.data && devices.data && checkins.data) {
    const deviceCode = resident.data.device.device_code;
    const device = deviceCode
      ? devices.data.items.find((d) => d.device_code === deviceCode)
      : undefined;
    if (!device) {
      return (
        <section className="panel pad stack" aria-label={DEVICE_SECTION}>
          <SectionState state="empty" message={deviceNoneAssigned(code)} />
        </section>
      );
    }
    return (
      <DevicePanel
        device={device}
        residentCode={code}
        events={checkins.data.items}
        meta={devices.data.meta}
      />
    );
  }

  const error = resident.error ?? devices.error ?? checkins.error;
  return (
    <section className="panel pad stack" aria-label={DEVICE_SECTION}>
      <QueryState
        panel={DEVICE_PANEL_NAME}
        isPending={!error}
        error={error}
        refetch={() => {
          if (resident.error) void resident.refetch();
          if (devices.error) void devices.refetch();
          if (checkins.error) void checkins.refetch();
        }}
      />
    </section>
  );
}
