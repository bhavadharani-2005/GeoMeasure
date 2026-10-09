import { MapPinOff } from "lucide-react";
import { Component, type ReactNode } from "react";
import { EmptyState } from "../ui/EmptyState";

/** Keeps the measurements usable if the map fails to render. */
export class MapBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error) {
    console.error("Map failed to render", error);
  }
  render() {
    if (this.state.failed) {
      return (
        <EmptyState icon={MapPinOff} title="Map unavailable">
          The map could not be displayed. Measurements below are still available.
        </EmptyState>
      );
    }
    return this.props.children;
  }
}
