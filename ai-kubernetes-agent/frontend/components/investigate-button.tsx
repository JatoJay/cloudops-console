"use client";

export function InvestigateButton() {
  function handleInvestigate() {
    // Kubernetes investigation is intentionally reserved for the next phase.
  }

  return (
    <button
      type="button"
      onClick={handleInvestigate}
      className="rounded-md bg-action px-8 py-5 text-lg font-bold text-white shadow-[0_1px_2px_rgba(8,39,84,0.12)] transition hover:bg-[#075bd9] focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-action/30 active:translate-y-px sm:min-w-[405px] sm:text-xl"
      aria-describedby="investigate-note"
    >
      Investigate Cluster
    </button>
  );
}
