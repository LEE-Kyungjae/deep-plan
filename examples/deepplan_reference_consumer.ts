type PlanEnvelope = {
  ok: boolean;
  tool_name: string;
  result_type: "plan";
  plan: {
    schema_version: string;
    version: string;
    goal: string;
    success_metric: string;
    deadline: string;
    [key: string]: unknown;
  };
  fingerprint: string;
  contract_version: string;
  implementation_version: string;
};

type CycleEnvelope = {
  ok: boolean;
  result_type: "cycle";
  plan: PlanEnvelope["plan"];
  fingerprint: string;
  contract_version: string;
  implementation_version: string;
  qa: {
    result: string;
    score: number;
  };
  health: {
    status: string;
  };
};

class DeepPlanHttpError extends Error {
  constructor(
    readonly status: number,
    readonly payload: Record<string, unknown>,
  ) {
    super(String(payload.error ?? `http_${status}`));
  }
}

class DeepPlanTsConsumer {
  constructor(private readonly baseUrl = "http://127.0.0.1:8787") {}

  async getPlan(): Promise<{ envelope: PlanEnvelope; etag: string }> {
    const response = await fetch(`${this.baseUrl}/plan`);
    const envelope = (await response.json()) as PlanEnvelope;
    if (!response.ok) {
      throw new DeepPlanHttpError(response.status, envelope as Record<string, unknown>);
    }
    return { envelope, etag: response.headers.get("etag") ?? "" };
  }

  async getCycle(limit = 5): Promise<CycleEnvelope> {
    const response = await fetch(`${this.baseUrl}/cycle?limit=${limit}`);
    const envelope = (await response.json()) as CycleEnvelope;
    if (!response.ok) {
      throw new DeepPlanHttpError(response.status, envelope as Record<string, unknown>);
    }
    return envelope;
  }

  async updatePlan(payload: Record<string, unknown>, etag: string): Promise<PlanEnvelope> {
    const response = await fetch(`${this.baseUrl}/plan`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "If-Match": etag,
      },
      body: JSON.stringify(payload),
    });
    const envelope = (await response.json()) as PlanEnvelope;
    if (!response.ok) {
      throw new DeepPlanHttpError(response.status, envelope as Record<string, unknown>);
    }
    return envelope;
  }
}

async function main(): Promise<void> {
  const client = new DeepPlanTsConsumer();
  const { envelope: before, etag } = await client.getPlan();

  console.log("contract_version:", before.contract_version);
  console.log("implementation_version:", before.implementation_version);
  console.log("goal_before:", before.plan.goal);

  const updated = await client.updatePlan(
    {
      goal: "Reference consumer updated goal",
      success_metric: "Reach 2 retained pilots",
      deadline: "2026-05-01",
    },
    etag,
  );

  const cycle = await client.getCycle(3);
  console.log("goal_after:", updated.plan.goal);
  console.log("fingerprint_after:", updated.fingerprint);
  console.log("qa_result:", cycle.qa.result);
  console.log("health_status:", cycle.health.status);
}

void main().catch((error) => {
  if (error instanceof DeepPlanHttpError) {
    console.error("deepplan_http_error", error.status, error.payload);
    process.exitCode = 1;
    return;
  }
  console.error(error);
  process.exitCode = 1;
});
