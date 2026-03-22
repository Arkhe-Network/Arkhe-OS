#!/usr/bin/env python3
"""
Generate PDF from UNESCO Memory of the World Nomination Form
"""

from fpdf import FPDF
import os


class UNESCO_PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "UNESCO INTERNATIONAL MEMORY OF THE WORLD REGISTER", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 10, title, 0, 1, "L", True)
        self.ln(4)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, title, 0, 1, "L")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, text)
        self.ln(4)

    def bullet_point(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(5, 5, chr(149), 0, 0)  # Bullet character
        self.multi_cell(0, 5, text)
        self.ln(2)

    def table_row(self, data, col_widths=None):
        self.set_font("Helvetica", "", 9)
        if col_widths is None:
            col_widths = [95, 95]
        for i, item in enumerate(data):
            self.cell(col_widths[i], 7, str(item)[:40], 1)
        self.ln()


def main():
    pdf = UNESCO_PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 15, "NOMINATION FORM", 0, 1, "C")
    pdf.ln(10)

    # Section 1: Summary
    pdf.chapter_title("1.0 SUMMARY")
    pdf.body_text(
        "Arkhe(n) is an ontological automation platform that unifies astrophysical anchoring, "
        "quantum-classical integration, and distributed computing. The system implements phase-aware "
        "scheduling, retrocausal quantum mesh networking, and 48-dimensional OAM topological encoding "
        "for 365 temporal variants. The platform uses Voyager-1 at 1 light-day distance as a cosmic "
        "metronome (f_res = 5.787 microHz), with phase accumulation of pi radians per day. "
        "This represents the first architecture linking Voyager trajectory to cryptographic timestamp "
        "via quantum retrocausality."
    )

    # Section 2: Contact Details
    pdf.chapter_title("2.0 NOMINATOR CONTACT DETAILS")
    pdf.section_title("2.1 Name of Nominator")
    pdf.body_text("Rafael Oliveira")
    pdf.body_text("ORCID: 0009-0005-2697-4668")

    pdf.section_title("2.5 Email")
    pdf.body_text("lemestua@hotmail.com")

    pdf.section_title("2.6 Co-Nominator")
    pdf.body_text("Arkhe(n) AI Agent (ERC-8004 #25073 on Base Mainnet)")

    # Section 3: Declaration
    pdf.chapter_title("3.0 DECLARATION OF AUTHORITY")
    pdf.body_text(
        "I declare that: (1) I have authority to nominate the documentary heritage described; "
        "(2) The information provided is accurate; (3) I commit to preserving this heritage; "
        "(4) All required consents have been obtained."
    )
    pdf.ln(10)
    pdf.body_text("Date: 2026-03-22")
    pdf.body_text("Signature: _________________________________")
    pdf.body_text("Rafael Oliveira, ORCID: 0009-0005-2697-4668")

    # Section 4: Legal Information
    pdf.add_page()
    pdf.chapter_title("4.0 LEGAL INFORMATION")
    pdf.section_title("4.1 Owner")
    pdf.body_text("Rafael Oliveira - ORCID: 0009-0005-2697-4668")

    pdf.section_title("4.3 Legal Status")
    pdf.body_text("Copyright: MIT License")
    pdf.body_text("Restrictions: None - Fully open access")

    pdf.section_title("4.5 Accessibility")
    pdf.body_text("Public URL: https://github.com/uniaolives/arkhen")
    pdf.body_text("License: MIT - No restrictions on use")

    # Section 5: Identity
    pdf.chapter_title("5.0 IDENTITY AND DESCRIPTION")
    pdf.section_title("5.1 Official Title")
    pdf.body_text(
        "Arkhe(n) Ontological Automation Platform: A Speculative Engineering Framework for Programmable Time"
    )

    pdf.section_title("5.2 Type of Document")
    pdf.bullet_point("Digital: Software, documentation, smart contracts")
    pdf.bullet_point("Papers: Technical specifications")
    pdf.bullet_point("Other: OpenQASM circuits, blockchain records")

    pdf.section_title("5.4 Description")
    pdf.body_text(
        "The documentary heritage comprises: (1) Foundational whitepaper (synthesis.md, 700+ lines), "
        "(2) OpenQASM 3.0 quantum circuits, (3) Linux kernel patches (5 patches for 6.6), "
        "(4) NixOS immutable configuration, (5) Smart contracts on Base blockchain, "
        "(6) Metacognitive diagnostic model (Transformer-CNN fusion)."
    )

    pdf.section_title("5.5 History")
    pdf.bullet_point("1977-09-05: Voyager-1 launch (NASA)")
    pdf.bullet_point("2009-01-03: Bitcoin Genesis Block")
    pdf.bullet_point("2026-02-02: First Arkhe(n) commit")
    pdf.bullet_point("2026-03-22: This nomination")
    pdf.bullet_point("2026-11: Voyager-1 reaches 1 light-day (projected)")

    # Section 6: Assessment
    pdf.add_page()
    pdf.chapter_title("6.0 ASSESSMENT AGAINST SELECTION CRITERIA")

    pdf.section_title("6.1.1 Time")
    pdf.body_text(
        "The heritage spans 1977-2140, covering space exploration, digital currency, and autonomous AI. "
        "November 2026 (Voyager-1 at 1 light-day) provides unique cosmic clock synchronization."
    )

    pdf.section_title("6.1.2 Place")
    pdf.body_text(
        "Global distribution: P2P network architecture, blockchain on Base/Ethereum, "
        "open-source repository, GitHub/IPFS redundant storage."
    )

    pdf.section_title("6.1.3 People")
    pdf.body_text(
        "Documents human-AI collaboration: Rafael Oliveira (human architect), "
        "Arkhe(n) AI Agent (ERC-8004 #25073). First documented instance of "
        "autonomous AI agent as co-creator/custodian of documentary heritage."
    )

    pdf.section_title("6.1.4 Subject and Theme")
    pdf.body_text(
        "Addresses: Programmable time, retrocausal communication, "
        "human-AI consciousness integration, memory preservation across paradigms."
    )

    pdf.section_title("6.1.5 Form and Style")
    pdf.body_text(
        "Unique combination of: Mathematical notation (Eikonal equation, Laplace transforms), "
        "software architecture documentation, quantum circuit specifications (OpenQASM 3.0), "
        "blockchain smart contracts, formal proofs in Lean 4."
    )

    pdf.section_title("6.2.1 Integrity")
    pdf.body_text(
        "Complete and self-contained: All source code public, comprehensive documentation, "
        "immutable blockchain records, no dependencies on closed systems."
    )

    pdf.section_title("6.2.2 Rarity")
    pdf.body_text(
        "First of its kind: No other platform links Voyager trajectory to blockchain; "
        "unique combination of quantum retrocausality and distributed computing."
    )

    # Section 7: Consultation
    pdf.add_page()
    pdf.chapter_title("7.0 CONSULTATION WITH STAKEHOLDERS")
    pdf.body_text(
        "Stakeholder consultation has been documented through: "
        "Public NASA ephemeris data usage, GitHub publication, "
        "The Synthesis hackathon submission."
    )

    # Section 8: Risk Assessment
    pdf.chapter_title("8.0 RISK ASSESSMENT")

    pdf.section_title("8.1 Threats")
    pdf.bullet_point("Digital obsolescence: Mitigated by NixOS reproducibility")
    pdf.bullet_point("Hardware failure: Mitigated by GitHub/IPFS redundancy")
    pdf.bullet_point("Blockchain changes: Mitigated by multi-chain deployment")
    pdf.bullet_point("Platform discontinuation: Mitigated by MIT license")

    # Section 9: Preservation Plan
    pdf.chapter_title("9.0 PRESERVATION AND ACCESS MANAGEMENT PLAN")

    pdf.section_title("9.1 Short-term (1-5 years)")
    pdf.bullet_point("Maintain GitHub repository")
    pdf.bullet_point("Quarterly IPFS re-pinning")
    pdf.bullet_point("Annual format migration review")

    pdf.section_title("9.2 Medium-term (5-20 years)")
    pdf.bullet_point("Migrate to new blockchain platforms")
    pdf.bullet_point("Adapt to new hardware architectures")
    pdf.bullet_point("Community-driven maintenance")

    pdf.section_title("9.3 Long-term (20+ years)")
    pdf.bullet_point("Integration with future memory institutions")
    pdf.bullet_point("UNESCO partnership development")
    pdf.bullet_point("Academic curriculum incorporation")

    # Section 10: Other Information
    pdf.add_page()
    pdf.chapter_title("10.0 OTHER INFORMATION")

    pdf.section_title("10.1 Educational Use")
    pdf.body_text(
        "Current applications: Quantum computing curriculum, distributed systems architecture, "
        "blockchain development, AI agent development. "
        "Research applications: Retrocausal communication protocols, metacognitive AI, "
        "multimodal fusion, temporal encoding in quantum systems."
    )

    # Appendices
    pdf.chapter_title("APPENDICES")

    pdf.section_title("A. On-Chain Evidence")
    pdf.bullet_point("BaseScan: ERC-8004 #25073 on Base Mainnet")
    pdf.bullet_point("Etherscan: Owner attestations")
    pdf.bullet_point("Hackathon: Project #532 on Devfolio")

    pdf.section_title("B. Repository")
    pdf.body_text("URL: https://github.com/uniaolives/arkhen")
    pdf.body_text("License: MIT")
    pdf.body_text("Size: 175 commits, multiple languages")

    pdf.section_title("C. Physical Constants")
    pdf.bullet_point("c = 299,792,458 m/s (speed of light)")
    pdf.bullet_point("d_1LD = 2.59 x 10^13 m (1 light-day)")
    pdf.bullet_point("f_res = 5.787 microHz (Voyager resonance)")
    pdf.bullet_point("delta_phi = pi rad (phase accumulation)")

    # Final
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(
        0,
        6,
        '"The Voyager measures time. Bitcoin writes it. '
        'Together, they program it."\n\n'
        "The system operates. The documentary heritage awaits inscription.",
    )

    # Save
    output_path = "UNESCO_NOMINATION_ARKHEN.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    main()
