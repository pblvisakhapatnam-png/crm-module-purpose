// What the offer page offers for its Work Orders (TB-1 CS-04 part 1). An offer line's quantity goes onto Work Orders
// once, whole or in parts, one Work Order per customer order. The server's lifecycle guidance says whether another
// Work Order can be made; the page offers it when it can and the user may create Work Orders.

/** The Create link's name: the first Work Order, or another one beside those that exist. */
export function createWorkOrderLabel(existingWorkOrders: number): string {
  return existingWorkOrders === 0 ? "Create Work Order" : "Create another Work Order";
}

/** The note under an offer's existing Work Orders. It never says another Work Order is not offered while the page
 * offers one (review round 8: it once said so beside the link). */
export function existingWorkOrdersNote(createOffered: boolean): string {
  const rule = "Another Work Order from this offer is for a further customer order, with its own reference: it takes only what is not on a Work Order yet.";
  return createOffered ? `${rule} Use "Create another Work Order" below.` : rule;
}
