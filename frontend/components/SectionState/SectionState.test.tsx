// req: FE-035, FE-140, FE-141, UX-200, UX-203
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/services/api";
import { QueryState, SectionState } from "./SectionState";

describe("SectionState", () => {
  it("renders loading with role status and empty text", () => {
    const { rerender } = render(<SectionState state="loading" message="Loading devices…" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading devices…");
    rerender(<SectionState state="empty" message="Nothing." />);
    expect(screen.getByText("Nothing.")).toBeVisible();
  });

  it("renders errors with Try again and the reference", async () => {
    const retry = vi.fn();
    render(
      <QueryState
        panel="devices"
        isPending={false}
        error={new ApiError({ status: 500, title: "x", requestId: "req-1" })}
        refetch={retry}
      />,
    );
    expect(
      screen.getByText("Could not load devices. Check your connection and try again."),
    ).toBeVisible();
    expect(screen.getByText("Reference: req-1")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
  });

  it("renders 403 as no access and loading while pending", () => {
    const { rerender, container } = render(
      <QueryState
        panel="x"
        isPending={false}
        error={new ApiError({ status: 403, title: "x" })}
        refetch={vi.fn()}
      />,
    );
    expect(screen.getByText("You do not have access to this information.")).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
    rerender(<QueryState panel="devices" isPending error={null} refetch={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading devices…");
    rerender(<QueryState panel="devices" isPending={false} error={null} refetch={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
