import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { decodeEntities, parseSnippet, SafeSnippet } from "./safe-snippet";

describe("parseSnippet", () => {
  it("highlights only <mark> regions", () => {
    expect(parseSnippet("the <mark>ice</mark> age")).toEqual([
      { text: "the ", mark: false },
      { text: "ice", mark: true },
      { text: " age", mark: false },
    ]);
  });

  it("decodes the entities the server uses when escaping", () => {
    expect(decodeEntities("a &lt;b&gt; &amp; &quot;c&quot; &#39;d&#39;")).toBe(`a <b> & "c" 'd'`);
  });

  it("tolerates unbalanced and stray tags", () => {
    expect(parseSnippet("</mark>x<mark>y")).toEqual([
      { text: "x", mark: false },
      { text: "y", mark: true },
    ]);
  });
});

describe("SafeSnippet (XSS)", () => {
  it("renders <mark> as a real element and everything else as text", () => {
    const { container } = render(<SafeSnippet snippet="say <mark>hello</mark> there" />);
    expect(container.querySelectorAll("mark")).toHaveLength(1);
    expect(container.querySelector("mark")?.textContent).toBe("hello");
    expect(container.textContent).toBe("say hello there");
  });

  it.each([
    "<script>alert(1)</script>",
    '<img src=x onerror="alert(1)">',
    '<a href="javascript:alert(1)">x</a>',
    "<iframe src=//evil></iframe>",
    "<mark><script>alert(1)</script></mark>",
    "<MARK onclick=alert(1)>x</MARK>",
    "<mark onmouseover=alert(1)>x</mark>",
    "<style>*{display:none}</style>",
    "<<mark>script>alert(1)<</mark>/script>",
  ])("never creates elements or attributes from server text: %s", (snippet) => {
    const { container } = render(<SafeSnippet snippet={snippet} />);
    const elements = Array.from(container.querySelectorAll("*"));
    // Only the wrapper span and (genuine, attribute-free) <mark> elements may exist.
    for (const el of elements) {
      expect(["SPAN", "MARK"]).toContain(el.tagName);
      const attrs = Array.from(el.attributes).map((a) => a.name);
      expect(attrs.filter((n) => n !== "class")).toEqual([]);
    }
    expect(container.querySelector("script,img,iframe,style,a")).toBeNull();
  });

  it("shows escaped markup as literal text, decoded once", () => {
    const { container } = render(
      <SafeSnippet snippet="&lt;script&gt;alert(1)&lt;/script&gt; <mark>x</mark>" />,
    );
    expect(container.textContent).toBe("<script>alert(1)</script> x");
    expect(container.querySelector("script")).toBeNull();
  });
});
