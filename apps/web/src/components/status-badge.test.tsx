import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./status-badge";
import { EmptyState, ErrorState } from "./states";

describe("StatusBadge", () => {
  it("renders the status text", () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText("completed")).toBeInTheDocument();
  });
  it("falls back for unknown statuses", () => {
    render(<StatusBadge status="storyboarding" />);
    expect(screen.getByText("storyboarding")).toBeInTheDocument();
  });
});

describe("states", () => {
  it("error state is announced as an alert", () => {
    render(<ErrorState message="boom" />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });
  it("empty state shows hint", () => {
    render(<EmptyState title="Nothing" hint="Create one" />);
    expect(screen.getByText("Create one")).toBeInTheDocument();
  });
});
