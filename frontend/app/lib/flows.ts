import { generateActions, getActions } from "./api";
import { ApiError, type ActionsResponse, type Week } from "./types";

/** The week's actions: reuse what was already generated, otherwise generate them now. */
export async function loadActions(id: string, week: Week): Promise<ActionsResponse> {
  try {
    const have = await getActions(id, week);
    if (have.actions.length > 0) return have;
  } catch (e) {
    if (!(e instanceof ApiError) || (e.status !== 404 && e.status !== 422)) throw e;   // nothing generated for this week yet
  }
  return generateActions(id, week);
}
