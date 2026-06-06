import { describe, expect, it } from "vitest";

import { parseRedditThreadDom, parseRedditThreadJson } from "../src/lib/reddit-parser";
import { assertJsonObject } from "../src/types/contracts";

const SOURCE_URL = "https://www.reddit.com/r/Coffee/comments/thread123/example.json";
const CAPTURED_AT = "2026-06-05T08:00:00.000Z";

describe("parseRedditThreadJson", () => {
  it("parses a thread, top-level comment, nested reply, and more node in traversal order", () => {
    const result = parseRedditThreadJson(buildThreadWithNestedReplies(), SOURCE_URL, {
      capturedAt: CAPTURED_AT
    });

    expect(result.stopReason).toBeNull();
    expect(result.moreNodeCount).toBe(1);
    expect(result.rawItems.map((item) => item.source_kind)).toEqual([
      "reddit_thread",
      "reddit_comment",
      "reddit_comment",
      "reddit_comment"
    ]);
    expect(result.rawItems.map((item) => item.source_object_id)).toEqual([
      "t3_thread123",
      "t1_comment456",
      "t1_reply789",
      "more_more123"
    ]);

    const [thread, topLevelComment, nestedReply, moreNode] = result.rawItems;

    expect(thread).toEqual(
      expect.objectContaining({
        platform: "reddit",
        source_kind: "reddit_thread",
        raw_schema_version: "raw_reddit_thread_v1",
        parser_version: "reddit-json-parser@0.1.0",
        captured_at: CAPTURED_AT
      })
    );
    expect(thread.raw_payload).toEqual(
      expect.objectContaining({
        name: "t3_thread123",
        id: "thread123",
        title: "Best grinder for espresso?",
        selftext: "I want a quieter grinder under $300.",
        author: "buyer_researcher",
        subreddit: "Coffee",
        subreddit_name_prefixed: "r/Coffee",
        created_utc: 1780602718,
        score: 42,
        upvote_ratio: 0.88,
        num_comments: 12,
        locked: false,
        archived: false,
        stickied: false,
        link_flair_text: "Buying Advice",
        permalink: "/r/Coffee/comments/thread123/example/",
        url: "https://www.reddit.com/r/Coffee/comments/thread123/example/",
        source_url: SOURCE_URL,
        captured_at: CAPTURED_AT
      })
    );

    expect(topLevelComment.raw_payload).toEqual(
      expect.objectContaining({
        name: "t1_comment456",
        id: "comment456",
        body: "The motor noise is the real issue.",
        author: "espresso_owner",
        parent_id: "t3_thread123",
        link_id: "t3_thread123",
        thread_id: "t3_thread123",
        depth: 0,
        created_utc: 1780602800,
        score: 7,
        is_submitter: false,
        controversiality: 0,
        subreddit: "Coffee",
        subreddit_name_prefixed: "r/Coffee",
        permalink: "/r/Coffee/comments/thread123/example/comment456/",
        comment_flair: "Owner",
        author_flair_text: "Fallback flair",
        source_url: SOURCE_URL,
        captured_at: CAPTURED_AT
      })
    );
    expect(nestedReply.raw_payload).toEqual(
      expect.objectContaining({
        name: "t1_reply789",
        id: "reply789",
        parent_id: "t1_comment456",
        link_id: "t3_thread123",
        thread_id: "t3_thread123",
        depth: 1,
        body: "Nested replies must be traversed.",
        source_url: SOURCE_URL,
        captured_at: CAPTURED_AT
      })
    );
    expect(moreNode.raw_payload).toEqual(
      expect.objectContaining({
        kind: "more",
        id: "more123",
        parent_id: "t1_comment456",
        thread_id: "t3_thread123",
        children: ["reply999", "reply1000"],
        depth: 1,
        source_url: SOURCE_URL,
        captured_at: CAPTURED_AT
      })
    );
  });

  it("accepts comments with replies set to an empty string", () => {
    const result = parseRedditThreadJson(
      [
        listing([{ kind: "t3", data: { name: "t3_thread123", id: "thread123", title: "Thread" } }]),
        listing([
          {
            kind: "t1",
            data: {
              name: "t1_comment456",
              id: "comment456",
              body: "No nested replies.",
              replies: ""
            }
          }
        ])
      ],
      SOURCE_URL,
      { capturedAt: CAPTURED_AT }
    );

    expect(result.stopReason).toBeNull();
    expect(result.moreNodeCount).toBe(0);
    expect(result.rawItems.map((item) => item.source_object_id)).toEqual([
      "t3_thread123",
      "t1_comment456"
    ]);
    expect(result.rawItems[1].raw_payload.thread_id).toBe("t3_thread123");
  });

  it("normalizes invalid comment thread linkage to the parsed thread fullname", () => {
    const result = parseRedditThreadJson(
      [
        listing([{ kind: "t3", data: { name: "t3_thread123", id: "thread123", title: "Thread" } }]),
        listing([
          {
            kind: "t1",
            data: {
              name: "t1_bad_linkage",
              id: "bad_linkage",
              body: "Original linkage should not break upload.",
              link_id: "not_a_thread",
              thread_id: "t3_other_thread",
              replies: ""
            }
          }
        ])
      ],
      SOURCE_URL,
      { capturedAt: CAPTURED_AT }
    );

    const commentPayload = result.rawItems[1].raw_payload;

    expect(commentPayload.link_id).toBe("t3_thread123");
    expect(commentPayload.thread_id).toBe("t3_thread123");
  });

  it("does not emit reddit_comment items when thread fullname cannot be derived", () => {
    const result = parseRedditThreadJson(
      [
        listing([{ kind: "t3", data: { title: "Anonymous thread id" } }]),
        listing([
          {
            kind: "t1",
            data: {
              name: "t1_comment456",
              body: "This cannot be uploaded without a t3 thread id.",
              replies: ""
            }
          },
          {
            kind: "more",
            data: {
              id: "more123",
              children: ["abc"]
            }
          }
        ])
      ],
      SOURCE_URL,
      { capturedAt: CAPTURED_AT }
    );

    expect(result.rawItems).toHaveLength(1);
    expect(result.rawItems[0].source_kind).toBe("reddit_thread");
    expect(result.rawItems[0].source_object_id).toMatch(/^reddit_missing_thread_id_[a-f0-9]{16}$/);
    expect(result.moreNodeCount).toBe(0);
  });

  it("generates a stable fallback for more nodes without an id and keeps children", () => {
    const first = parseRedditThreadJson(buildMoreWithoutIdPayload(), SOURCE_URL, {
      capturedAt: CAPTURED_AT
    });
    const second = parseRedditThreadJson(
      [
        listing([{ kind: "t3", data: { id: "thread123", name: "t3_thread123" } }]),
        listing([
          {
            kind: "more",
            data: {
              depth: 1,
              children: ["abc", "def"],
              parent_id: "t1_parent999"
            }
          }
        ])
      ],
      SOURCE_URL,
      { capturedAt: CAPTURED_AT }
    );

    const firstMoreNode = first.rawItems[1];
    const secondMoreNode = second.rawItems[1];

    expect(first.moreNodeCount).toBe(1);
    expect(firstMoreNode.source_object_id).toMatch(/^more_missing_id_[a-f0-9]{16}$/);
    expect(firstMoreNode.source_object_id).toBe(secondMoreNode.source_object_id);
    expect(firstMoreNode.raw_payload.thread_id).toBe("t3_thread123");
    expect(firstMoreNode.raw_payload.children).toEqual(["abc", "def"]);
  });

  it("returns invalid_payload without throwing for malformed input", () => {
    const result = parseRedditThreadJson({ data: { children: [] } }, SOURCE_URL, {
      capturedAt: CAPTURED_AT
    });

    expect(result).toEqual({
      rawItems: [],
      moreNodeCount: 0,
      stopReason: "invalid_payload"
    });
  });

  it("returns missing_thread when listings are valid but no thread node exists", () => {
    const result = parseRedditThreadJson(
      [listing([{ kind: "t1", data: { name: "t1_comment_only" } }]), listing([])],
      SOURCE_URL,
      { capturedAt: CAPTURED_AT }
    );

    expect(result).toEqual({
      rawItems: [],
      moreNodeCount: 0,
      stopReason: "missing_thread"
    });
  });

  it("cleans non-JSON values before asserting raw_payload as a JsonObject", () => {
    const result = parseRedditThreadJson(
      [
        listing([
          {
            kind: "t3",
            data: {
              name: "t3_dirty",
              id: "dirty",
              title: "Dirty payload",
              selftext: "Parser should clean selected fields.",
              author: undefined,
              created_utc: Number.NEGATIVE_INFINITY,
              score: Number.NaN,
              upvote_ratio: Number.POSITIVE_INFINITY,
              callback: () => "not-json"
            }
          }
        ]),
        listing([])
      ],
      SOURCE_URL,
      { capturedAt: CAPTURED_AT }
    );

    const rawPayload = result.rawItems[0].raw_payload;

    expect(rawPayload).toEqual(
      expect.objectContaining({
        created_utc: null,
        score: null,
        upvote_ratio: null
      })
    );
    expect(rawPayload).not.toHaveProperty("author");
    expect(rawPayload).not.toHaveProperty("callback");
    expect(() => assertJsonObject(rawPayload)).not.toThrow();
    expectJsonSafe(rawPayload);
  });

  it("falls back from invalid capturedAt and keeps item and payload timestamps consistent", () => {
    const result = parseRedditThreadJson(buildMoreWithoutIdPayload(), SOURCE_URL, {
      capturedAt: "not-a-date"
    });

    const [thread, moreNode] = result.rawItems;

    expect(thread.captured_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(thread.raw_payload.captured_at).toBe(thread.captured_at);
    expect(moreNode.raw_payload.captured_at).toBe(moreNode.captured_at);
  });

  it("produces stable raw_payload_hash values for the same payload", () => {
    const first = parseRedditThreadJson(buildThreadWithNestedReplies(), SOURCE_URL, {
      capturedAt: CAPTURED_AT
    });
    const second = parseRedditThreadJson(buildThreadWithNestedReplies(), SOURCE_URL, {
      capturedAt: CAPTURED_AT
    });

    expect(first.rawItems.map((item) => item.raw_payload_hash)).toEqual(
      second.rawItems.map((item) => item.raw_payload_hash)
    );
  });
});

describe("parseRedditThreadDom", () => {
  it("parses an old Reddit DOM thread and loaded comments as schema-compatible raw items", () => {
    document.body.innerHTML = oldRedditThreadHtml();

    const result = parseRedditThreadDom(
      document,
      "https://old.reddit.com/r/Coffee/comments/thread123/best_grinder/",
      "thread123",
      { capturedAt: CAPTURED_AT }
    );

    expect(result.stopReason).toBeNull();
    expect(result.commentNodeCount).toBe(2);
    expect(result.rawItems.map((item) => item.source_object_id)).toEqual([
      "t3_thread123",
      "t1_comment456",
      "t1_reply789"
    ]);
    expect(result.rawItems.map((item) => item.parser_version)).toEqual([
      "reddit-dom-parser@0.1.0",
      "reddit-dom-parser@0.1.0",
      "reddit-dom-parser@0.1.0"
    ]);

    const [thread, topLevelComment, nestedReply] = result.rawItems;
    expect(thread.raw_payload).toEqual(
      expect.objectContaining({
        name: "t3_thread123",
        id: "thread123",
        title: "Best grinder for espresso?",
        selftext: "I want a quieter grinder under $300.",
        author: "buyer_researcher",
        subreddit: "Coffee",
        subreddit_name_prefixed: "r/Coffee",
        num_comments: 2,
        source_url: "https://old.reddit.com/r/Coffee/comments/thread123/best_grinder/"
      })
    );
    expect(topLevelComment.raw_payload).toEqual(
      expect.objectContaining({
        name: "t1_comment456",
        body: "The motor noise is the real issue.",
        author: "espresso_owner",
        parent_id: "t3_thread123",
        link_id: "t3_thread123",
        thread_id: "t3_thread123",
        depth: 0,
        score: 7,
        created_utc: 1780646800,
        subreddit: "Coffee"
      })
    );
    expect(nestedReply.raw_payload).toEqual(
      expect.objectContaining({
        name: "t1_reply789",
        parent_id: "t1_comment456",
        depth: 1,
        body: "Nested replies must be traversed."
      })
    );
  });

  it("does not treat Reddit network policy block pages as thread evidence", () => {
    document.body.innerHTML = `
      <h1>whoa there, pardner!</h1>
      <p>Your request has been blocked due to a network policy.</p>
    `;

    const result = parseRedditThreadDom(
      document,
      "https://old.reddit.com/r/Coffee/comments/thread123/best_grinder/",
      "thread123",
      { capturedAt: CAPTURED_AT }
    );

    expect(result).toEqual({
      rawItems: [],
      commentNodeCount: 0,
      stopReason: "missing_thread_dom"
    });
  });
});

function buildThreadWithNestedReplies(): unknown {
  return [
    listing([
      {
        kind: "t3",
        data: {
          name: "t3_thread123",
          id: "thread123",
          title: "Best grinder for espresso?",
          selftext: "I want a quieter grinder under $300.",
          author: "buyer_researcher",
          subreddit: "Coffee",
          subreddit_name_prefixed: "r/Coffee",
          created_utc: 1780602718,
          score: 42,
          upvote_ratio: 0.88,
          num_comments: 12,
          locked: false,
          archived: false,
          stickied: false,
          link_flair_text: "Buying Advice",
          permalink: "/r/Coffee/comments/thread123/example/",
          url: "https://www.reddit.com/r/Coffee/comments/thread123/example/"
        }
      }
    ]),
    listing([
      {
        kind: "t1",
        data: {
          name: "t1_comment456",
          id: "comment456",
          body: "The motor noise is the real issue.",
          author: "espresso_owner",
          parent_id: "t3_thread123",
          link_id: "t3_thread123",
          depth: 0,
          created_utc: 1780602800,
          score: 7,
          is_submitter: false,
          controversiality: 0,
          subreddit: "Coffee",
          subreddit_name_prefixed: "r/Coffee",
          permalink: "/r/Coffee/comments/thread123/example/comment456/",
          comment_flair: "Owner",
          author_flair_text: "Fallback flair",
          replies: listing([
            {
              kind: "t1",
              data: {
                name: "t1_reply789",
                id: "reply789",
                parent_id: "t1_comment456",
                link_id: "t3_thread123",
                depth: 1,
                body: "Nested replies must be traversed.",
                replies: ""
              }
            },
            {
              kind: "more",
              data: {
                id: "more123",
                parent_id: "t1_comment456",
                children: ["reply999", "reply1000"],
                depth: 1
              }
            }
          ])
        }
      }
    ])
  ];
}

function buildMoreWithoutIdPayload(): unknown {
  return [
    listing([{ kind: "t3", data: { name: "t3_thread123", id: "thread123" } }]),
    listing([
      {
        kind: "more",
        data: {
          parent_id: "t1_parent999",
          children: ["abc", "def"],
          depth: 1
        }
      }
    ])
  ];
}

function listing(children: unknown[]): unknown {
  return {
    kind: "Listing",
    data: {
      children
    }
  };
}

function oldRedditThreadHtml(): string {
  return `
    <main>
      <div class="thing link" data-fullname="t3_thread123">
        <a class="title">Best grinder for espresso?</a>
        <a class="author">buyer_researcher</a>
        <div class="usertext-body"><div class="md">I want a quieter grinder under $300.</div></div>
      </div>
      <div class="comment" data-fullname="t1_comment456" data-parent="t3_thread123" data-author="espresso_owner" data-depth="0">
        <a class="author">espresso_owner</a>
        <span class="score unvoted">7 points</span>
        <time datetime="2026-06-05T08:06:40.000Z"></time>
        <a class="bylink" href="/r/Coffee/comments/thread123/best_grinder/comment456/">permalink</a>
        <div class="usertext-body"><div class="md">The motor noise is the real issue.</div></div>
        <div class="child">
          <div class="comment" data-fullname="t1_reply789" data-parent="t1_comment456" data-depth="1">
            <div class="usertext-body"><div class="md">Nested replies must be traversed.</div></div>
          </div>
        </div>
      </div>
    </main>
  `;
}

function expectJsonSafe(value: unknown): void {
  if (value === null) {
    return;
  }

  switch (typeof value) {
    case "string":
    case "boolean":
      return;
    case "number":
      expect(Number.isFinite(value)).toBe(true);
      return;
    case "object":
      if (Array.isArray(value)) {
        for (const item of value) {
          expectJsonSafe(item);
        }
        return;
      }
      expect(Object.getPrototypeOf(value)).toBe(Object.prototype);
      for (const [key, nestedValue] of Object.entries(value)) {
        expect(typeof key).toBe("string");
        expectJsonSafe(nestedValue);
      }
      return;
    default:
      expect.unreachable(`non-json value type: ${typeof value}`);
  }
}
