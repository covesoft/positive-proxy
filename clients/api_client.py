# file: /positive-proxy/clients/discord/api_client.py
copyright = """
    Positive Proxy is a bill-making and voting system that allows voters to pass their ballot to trusted parties to vote on their behalf.
    Copyright (C) 2026  Joel Spector

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>."""

import httpx
from uuid import UUID
from typing import Optional, List, Dict, Any

# Use this file as such:
# from discord_bot.api_client import PositiveProxyClient
# bot.proxy_api = PositiveProxyClient(base_url="http://localhost:8000")

class PositiveProxyClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        Initializes the async API client wrapper to connect Discord to the Ledger Backend.
        """
        self.base_url = base_url.rstrip("/")

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Internal helper to manage async requests and error handling safely."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            response = await client.request(method, url, **kwargs)
            
            if response.status_code >= 400:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                raise Exception(f"Backend API Error ({response.status_code}): {error_detail}")
                
            return response.json()

    # =========================================================================
    # USER & PROXY ENDPOINTS
    # =========================================================================

    async def create_user(self, username: str) -> Dict[str, Any]:
        """Maps to POST /users/ - Registers a new citizen on the ledger."""
        return await self._request("POST", "/users/", json={"username": username})

    async def assign_proxy(self, user_id: UUID, proxy_to_id: UUID, proposal_id: Optional[UUID] = None, is_transferable: bool = True) -> Dict[str, Any]:
        """Maps to POST /users/{id}/proxy - Assigns a global or bill-specific proxy."""
        payload = {
            "proxy_to_id": str(proxy_to_id),
            "proposal_id": str(proposal_id) if proposal_id else None,
            "is_transferable": is_transferable
        }
        return await self._request("POST", f"/users/{user_id}/proxy", json=payload)

    async def get_pending_actions(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Maps to GET /users/{id}/pending-actions - Tells a user what bills need attention."""
        return await self._request("GET", f"/users/{user_id}/pending-actions")

    async def get_user_alerts(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Maps to GET /users/{id}/alerts - Finds out if their proxy voted against their intent."""
        return await self._request("GET", f"/users/{user_id}/alerts")

    # =========================================================================
    # PROPOSAL & VOTING ENDPOINTS
    # =========================================================================

    async def submit_issue(self, creator_id: UUID, title: str, description: str) -> Dict[str, Any]:
        """Maps to POST /proposals/issues - Anchors a public civic problem entry."""
        return await self._request(
            "POST", 
            "/proposals/issues", 
            params={"creator_id": str(creator_id)}, 
            json={"title": title, "description": description}
        )

    async def submit_proposal(self, author_id: UUID, title: str, issue_ids: List[UUID], parent_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Maps to POST /proposals/ - Drafts a new proposal or structural fork."""
        payload = {
            "title": title,
            "issue_ids": [str(i) for i in issue_ids],
            "parent_id": str(parent_id) if parent_id else None
        }
        return await self._request(
            "POST", 
            "/proposals/", 
            params={"author_id": str(author_id)}, 
            json=payload
        )

    async def fork_proposal(self, parent_id: UUID, author_id: UUID, fork_title: str) -> Dict[str, Any]:
        """Maps to POST /proposals/{parent_id}/fork - Git-like branch of an existing proposal."""
        return await self._request(
            "POST", 
            f"/proposals/{parent_id}/fork", 
            params={"author_id": str(author_id), "fork_title": fork_title}
        )

    async def submit_section_edit(self, proposal_id: UUID, user_id: UUID, section_number: int, content: str) -> Dict[str, Any]:
        """Maps to POST /proposals/{id}/sections - Commits line alterations to working drafts."""
        payload = {
            "section_number": section_number,
            "content": content
        }
        return await self._request(
            "POST", 
            f"/proposals/{proposal_id}/sections", 
            params={"user_id": str(user_id)}, 
            json=payload
        )

    async def cast_vote(self, proposal_id: UUID, voter_id: UUID, vote_choice: str) -> Dict[str, Any]:
        """Maps to POST /proposals/{id}/vote - Casts a direct ballot, overriding proxy paths."""
        return await self._request(
            "POST", 
            f"/proposals/{proposal_id}/vote", 
            params={"voter_id": str(voter_id)}, 
            json={"vote_choice": vote_choice}
        )

    async def trace_vote(self, proposal_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Maps to GET /proposals/{id}/trace/{user_id} - Follows down the delegation path."""
        return await self._request("GET", f"/proposals/{proposal_id}/trace/{user_id}")

    async def get_proposal_turnout(self, proposal_id: UUID) -> Dict[str, Any]:
        """Maps to GET /proposals/{id}/turnout - Fetches global turnout matrix data."""
        return await self._request("GET", f"/proposals/{proposal_id}/turnout")

    async def get_proxy_volume(self, proposal_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Maps to GET /proposals/{id}/proxy-volume/{user_id} - Reads representative's anonymous weight."""
        return await self._request("GET", f"/proposals/{proposal_id}/proxy-volume/{user_id}")

    # =========================================================================
    # CRYPTOGRAPHIC AUDIT ENDPOINTS
    # =========================================================================

    async def get_ledger_snapshot(self) -> Dict[str, Any]:
        """Maps to GET /audit/snapshot - Generates global immutable state block-hash."""
        return await self._request("GET", "/audit/snapshot")

    async def verify_proposal_integrity(self, proposal_id: UUID) -> Dict[str, Any]:
        """Maps to GET /audit/proposal/{id}/verify - Runs deep anti-tampering verification."""
        return await self._request("GET", f"/audit/proposal/{proposal_id}/verify")

### EOF: /positive-proxy/clients/discord/api_client.py ###