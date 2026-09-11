import { describe, expect, it } from "vitest";
import { ApiError, errorFromResponse } from "../api";

describe("errorFromResponse", () => {
  it("maps the §5 envelope to a typed ApiError", () => {
    const err = errorFromResponse(
      402,
      JSON.stringify({ error: { code: "insufficient_credits", message: "You have 0 credits.", details: { available: 0 } } }),
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(402);
    expect(err.code).toBe("insufficient_credits");
    expect(err.message).toBe("You have 0 credits.");
    expect(err.details).toEqual({ available: 0 });
    expect(err.isNotFound).toBe(false);
  });

  it("falls back to the status table when the body is not an envelope", () => {
    expect(errorFromResponse(404, "<html>nope</html>").code).toBe("not_found");
    expect(errorFromResponse(404, "").isNotFound).toBe(true);
    expect(errorFromResponse(429, "{}").code).toBe("rate_limited");
    expect(errorFromResponse(418, "{}").code).toBe("internal_error");
  });
});
