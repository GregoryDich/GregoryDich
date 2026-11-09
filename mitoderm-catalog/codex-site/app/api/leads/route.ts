import { env } from "cloudflare:workers";
import { handleLeadRequest } from "@/lib/leads.server";

export function POST(request: Request) {
  return handleLeadRequest(request, env.DB);
}

export function GET(request: Request) {
  return handleLeadRequest(request, env.DB);
}
