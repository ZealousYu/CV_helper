import type { QANode } from './types'

export function findNode(tree: QANode[], nodeId: string): QANode | null {
  for (const node of tree) {
    if (node.nodeId === nodeId) return node
    const found = findNode(node.children, nodeId)
    if (found) return found
  }
  return null
}

export function findParent(tree: QANode[], nodeId: string, parent: QANode | null = null): QANode | null {
  for (const node of tree) {
    if (node.nodeId === nodeId) return parent
    const found = findParent(node.children, nodeId, node)
    if (found !== null) return found
  }
  return null
}

export function addChildNode(tree: QANode[], parentId: string, child: QANode): QANode[] {
  return tree.map((node) => {
    if (node.nodeId === parentId) {
      return { ...node, children: [...node.children, child] }
    }
    return { ...node, children: addChildNode(node.children, parentId, child) }
  })
}

export function updateNode(tree: QANode[], nodeId: string, patch: Partial<QANode>): QANode[] {
  return tree.map((node) => {
    if (node.nodeId === nodeId) {
      return { ...node, ...patch }
    }
    return { ...node, children: updateNode(node.children, nodeId, patch) }
  })
}

export function collectAllNodes(tree: QANode[]): QANode[] {
  const result: QANode[] = []
  const walk = (nodes: QANode[]) => {
    for (const n of nodes) {
      result.push(n)
      walk(n.children)
    }
  }
  walk(tree)
  return result
}

export function generateNodeId(parentId: string | null, siblings: QANode[]): string {
  if (!parentId) {
    const nums = siblings.map((s) => parseInt(s.nodeId.replace('q', ''), 10)).filter((n) => !isNaN(n))
    const next = nums.length ? Math.max(...nums) + 1 : 1
    return `q${next}`
  }
  const childNums = siblings
    .map((s) => {
      const suffix = s.nodeId.replace(`${parentId}.`, '')
      return parseInt(suffix, 10)
    })
    .filter((n) => !isNaN(n))
  const next = childNums.length ? Math.max(...childNums) + 1 : 1
  return `${parentId}.${next}`
}
