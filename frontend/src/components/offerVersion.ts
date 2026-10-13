// How a Commercial Offer version is named on screen: "CO-000123 v2" (Slice 9F). Versions share the offer code, so the
// code alone does not say which version an offer - or a Work Order made from one - is. With no version known, the code
// alone.

export function offerVersionLabel(offerCode: string, versionNumber?: number | null): string {
  return versionNumber ? `${offerCode} v${versionNumber}` : offerCode;
}
