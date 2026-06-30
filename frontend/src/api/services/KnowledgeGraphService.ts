import type { KGNodeOut } from '../models/KGNodeOut'
import type { KGEdgeOut } from '../models/KGEdgeOut'
import type { KGGraphOut } from '../models/KGGraphOut'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'

export type KGGraphCreate = { name: string; description?: string | null }
export type KGGraphUpdate = { name?: string; description?: string | null }

export type KGNodeCreate = {
  name: string
  type?: string
  description?: string | null
  properties?: Record<string, unknown> | null
}

export type KGNodeUpdate = {
  name?: string
  type?: string
  description?: string | null
  properties?: Record<string, unknown> | null
}

export type KGEdgeCreate = {
  source_node_id?: number | null
  target_node_id?: number | null
  source_name?: string | null
  target_name?: string | null
  relation: string
}

export type KGGraphDataOut = {
  nodes: KGNodeOut[]
  edges: KGEdgeOut[]
}

export type KGExtractPreview = {
  nodes: { name: string; type: string; description?: string | null }[]
  edges: { source_name?: string; target_name?: string; relation: string }[]
}

export class KnowledgeGraphService {
  // ---- Graphs ----
  public static listGraphs(): CancelablePromise<KGGraphOut[]> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/knowledge-graph/graphs',
    })
  }

  public static createGraph(data: KGGraphCreate): CancelablePromise<KGGraphOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/knowledge-graph/graphs',
      body: data,
      mediaType: 'application/json',
    })
  }

  public static updateGraph(graphId: number, data: KGGraphUpdate): CancelablePromise<KGGraphOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}',
      path: { graph_id: graphId },
      body: data,
      mediaType: 'application/json',
    })
  }

  public static deleteGraph(graphId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}',
      path: { graph_id: graphId },
    })
  }

  // ---- Nodes ----
  public static listNodes(
    graphId: number,
    search?: string,
    type?: string
  ): CancelablePromise<KGNodeOut[]> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}/nodes',
      path: { graph_id: graphId },
      query: { search, type },
    })
  }

  public static createNode(graphId: number, data: KGNodeCreate): CancelablePromise<KGNodeOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}/nodes',
      path: { graph_id: graphId },
      body: data,
      mediaType: 'application/json',
    })
  }

  public static updateNode(nodeId: number, data: KGNodeUpdate): CancelablePromise<KGNodeOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/knowledge-graph/nodes/{node_id}',
      path: { node_id: nodeId },
      body: data,
      mediaType: 'application/json',
    })
  }

  public static deleteNode(nodeId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/knowledge-graph/nodes/{node_id}',
      path: { node_id: nodeId },
    })
  }

  // ---- Edges ----
  public static listEdges(graphId: number): CancelablePromise<KGEdgeOut[]> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}/edges',
      path: { graph_id: graphId },
    })
  }

  public static createEdge(graphId: number, data: KGEdgeCreate): CancelablePromise<KGEdgeOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}/edges',
      path: { graph_id: graphId },
      body: data,
      mediaType: 'application/json',
    })
  }

  public static deleteEdge(edgeId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/knowledge-graph/edges/{edge_id}',
      path: { edge_id: edgeId },
    })
  }

  // ---- Full graph ----
  public static getFullGraph(graphId: number): CancelablePromise<KGGraphDataOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}/graph',
      path: { graph_id: graphId },
    })
  }

  // ---- Export ----
  public static async exportCypher(graphId: number): Promise<string> {
    const token =
      typeof OpenAPI.TOKEN === 'function'
        ? await OpenAPI.TOKEN({ method: 'GET', url: '' })
        : (OpenAPI.TOKEN ?? '')
    const resp = await fetch(
      `${OpenAPI.BASE}/api/v1/knowledge-graph/graphs/${graphId}/export/cypher`,
      {
        method: 'GET',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: OpenAPI.WITH_CREDENTIALS ? 'include' : 'same-origin',
      }
    )
    if (!resp.ok) throw new Error(`Export failed: ${resp.status}`)
    return resp.text()
  }

  // ---- Extract ----
  public static extractFromText(
    graphId: number,
    text: string,
    agentId: number
  ): CancelablePromise<KGExtractPreview> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/knowledge-graph/graphs/{graph_id}/extract',
      path: { graph_id: graphId },
      body: { text, agent_id: agentId },
      mediaType: 'application/json',
    })
  }
}
