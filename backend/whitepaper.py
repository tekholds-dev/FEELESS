"""One source of truth for the web whitepaper and its actual PDF."""
import io
import os
from pathlib import Path
from xml.sax.saxutils import escape
from fastapi import APIRouter, Response
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Table, TableStyle
from reportlab.lib.pagesizes import A4

CHAPTERS = [
('Executive Summary', 'FEELESS is building an economic fee-back layer around on-chain activity, supported by a market-intelligence terminal and an ecosystem discovery globe. FEELESS is the platform; $FEE is its core ecosystem asset; Fee-Back is the economic fee-return system; FEECAT is the culture, community and Fee-Back distribution layer. The goal is less noise, more useful context and more value returned to qualifying participants. This document distinguishes working software, approved product policy and planned infrastructure. It is not an offering document or a guarantee of investment returns.'),
('The Problem With On-Chain Fees', 'Transactions can incur blockchain network fees, DEX charges, aggregator fees, priority fees and other provider costs. Those charges vary by route and market conditions. Fragmented interfaces can make it difficult to distinguish an estimate from a settled fee, or a promotional reward from a documented entitlement. FEELESS does not solve this problem by pretending gas does not exist. Its proposed Fee-Back layer records qualifying fee value and returns that eligible value under explicit program rules.'),
('What FEELESS Is', 'FEELESS combines an ecosystem map, provider-backed market intelligence, token discovery, trading tools and community context. The terminal connects those layers in one workspace. Its long-term economic model is intended to make qualifying activity economically fee-less through Fee-Back, not to erase third-party charges. The product is non-custodial: wallet keys remain with the user.'),
('What FEELESS Is NOT', 'FEELESS is not a promise of zero blockchain gas, a guaranteed-profit scheme, a bank account or an investment-return product. It does not guarantee token value, liquidity, exchange listings or execution at a displayed chart price. Fee-Back is not yield or a holder return. Public chat handles and token listings are not identity verification, endorsement or contract safety certification.'),
('The FEELESS Terminal', 'The terminal is the intelligence and trading layer. Its default center asset is $FEE, never a randomly selected trending token. When the supplied contract has a provider-indexed market, the interface uses actual pair data and OHLCV candles. Otherwise it displays awaiting-market or provider-unavailable states. The surrounding workspace includes contextual discovery, new-pool feeds, Alpha Tape, watchlists, conditional alerts, token intelligence and explicit provider status.'),
('The Global Ecosystem Globe', 'The globe is the discovery layer and a context switcher. Selecting a supported chain or launchpad updates the terminal context, including feeds, rooms, provider scope, explorer destinations and market filters. The context persists between globe and terminal. Node coordinates form a visual map, not a claim about an organisation’s physical location. Launchpad provenance is shown only when the source can establish it; a DEX pool does not automatically prove its launchpad of origin.'),
('The $FEE Ecosystem Asset', '$FEE is the core FEELESS ecosystem asset. Owner-supplied Solana mint addresses are listed in the contract registry in this document. Market matching uses exact mint addresses rather than ticker names. An indexed market does not establish an audit, future utility, circulating supply accuracy or official third-party endorsement. RFEE is separately identified by its supplied mint; no undocumented rights or mechanism are assigned to it.'),
('$FEE Tokenomics', 'The approved allocation policy is 70% Liquidity & Ecosystem, 15% Marketing & Growth, 10% Team & Development, and 5% Community & Airdrops, totalling 100%. The approved launch model is no private sale and fair launch. Liquidity & Ecosystem supports market infrastructure and ecosystem development; Marketing & Growth supports awareness and adoption; Team & Development supports product delivery; Community & Airdrops supports participation. These percentages are policy, not an assertion that on-chain balances already match the allocations. Total supply, circulating supply, vesting, custody and implementation schedules require verified publication; the interface never invents them.'),
('Fee-Back Architecture', 'FEELESS intends to return 100% of eligible tracked fees to the qualifying user as the equivalent dollar amount in FEECAT. Eligible tracked fees are a defined subset established by program rules, not automatically every network, DEX or provider fee. The transaction can still incur normal charges. The intended lifecycle is trade, fee detection, eligibility verification, eligible USD value recording, FEECAT equivalent calculation, distribution and Fee-Back completion. The distribution program remains planned until its rules and infrastructure are activated.'),
('How Eligible Fees Are Tracked', 'A production implementation must establish the authoritative fee source, qualifying activity, wallet entitlement, eligibility period, exclusions, valuation timestamp, settlement finality, deduplication rules, rounding and distribution schedule. Each record should reference the underlying transaction and retain the source of the fee value. Quoted fees are estimates, not proof of settled charges or eligibility. Failed, reversed, duplicated or ineligible activity must not create a reward entitlement. The current interface does not classify an ordinary DEX fee as automatically eligible.'),
('How FeeCat Makes the Fee-Back Experience Work', 'Illustrative policy example, not a real payment: a user incurs $60 in eligible tracked fees. The Fee-Back record is $60. At the defined distribution point, the system uses a verified FEECAT reference price to calculate the token quantity representing that $60 eligible value: FEECAT quantity = eligible USD value / verified USD price per FEECAT, subject to published rounding rules. If that verified price is unavailable, quantity is unavailable; the system must not invent it. FEECAT market value can change after distribution. This is not guaranteed profit or a guaranteed future investment return.'),
('FeeCat', 'FeeCat is the first cat of FEELESS: the culture layer, the community layer and the proposed Fee-Back delivery layer. Its concept is fun, culture, utility and more for you. The FeeCat command center separates observed token-market status from the planned distribution program. Distribution history, received amounts and treasury information must come from verifiable records. Missions and educational progress may be browser-local participation tools; they create no token entitlement unless an actual published program explicitly provides one.'),
('Trading & Routing Architecture', 'The initial in-app execution integration is Solana through Jupiter and an injected Phantom wallet. The application requests a current order, displays available route and fee information, checks expiry and slippage, simulates without broadcasting, asks the user to approve the transaction in the wallet, and submits the unchanged signed transaction through the provider. A confirmed state requires an error-free on-chain confirmation. Non-Solana networks remain intelligence-only unless a supported execution integration is explicitly added. No route is guaranteed to remain executable.'),
('Market Data Architecture', 'DexScreener provides exact-address discovery and pair snapshots. GeckoTerminal provides pool discovery and OHLCV history. Jupiter supplies swap orders and routing information. Solana RPC supplies mint/account and transaction confirmation data where available. Server-side caches preserve source timestamps; stale and unavailable data is labelled. Alpha Tape contains actual provider observations, same-source snapshot deltas and verified chat contract mentions. It does not invent individual large trades, wallet movements, liquidity transactions, migrations or all-time highs that the connected sources cannot establish.'),
('Supported Ecosystems', 'Discovery contexts include Solana, Ethereum, Base, BNB Chain, Arbitrum, Avalanche, Polygon and Sui, subject to provider coverage. Launchpad contexts include Pump.fun, LetsBONK, Raydium LaunchLab, Meteora, Moonit and Four.meme. New pools are not necessarily new tokens or new launches. Listings are not exhaustive, and a missing pool does not prove that a token is inactive. Launchpad-specific data may be unavailable even when parent-chain data exists.'),
('Community / Trenches', 'The Trenches are the community layer. Contextual General, Alpha, Launches, Trading, Whales and New Pools rooms use persistent polling chat. There are no fabricated users or seeded conversations. Contract-address mentions are resolved to exact provider matches and connected to token cards, chart selection and Alpha Tape. Public handles are pseudonymous and unauthenticated; activity-based rankings measure messages, not verified people or investment expertise. Moderation and stronger identity tools are future work.'),
('Security Principles', 'Market information and community content must be treated as untrusted inputs. Provider URLs and supported RPC methods are controlled server-side. API credentials are not sent to the browser. Transactions require explicit wallet approval, exact-message matching, successful simulation and protection against duplicate submission. No software release is described as audited without an actual independent audit. Contract risk, malicious tokens, provider outages and application vulnerabilities remain possible.'),
('Wallet & Transaction Principles', 'FEELESS never needs a seed phrase or private key. Connecting a wallet exposes a public account only; signing a transaction is a separate, explicit action. The user should review the wallet prompt, asset pair, amount, minimum output, slippage and applicable fees. A cancelled signature does not trigger submission. Submitted but unconfirmed transactions remain pending or uncertain until checked; the application must not blindly resubmit them. Public RPC endpoints can rate-limit or become unavailable, in which case execution must fail safely.'),
('Revenue Model', 'Potential platform revenue sources include liquidity-related revenue, first-time-buyer or referral commissions, Pro tools, developer/API products, ecosystem partnerships, on/off-ramp referrals and B2B/service products. These are potential sources, not booked revenue or guarantees. Any future holder or community program and platform revenue must remain separate from Fee-Back eligibility and distribution accounting. Fees, conflicts and referral relationships should be disclosed when implemented.'),
('Transparency Principles', 'The interface distinguishes LIVE, TESTING, BUILDING, PLANNED, AWAITING MARKET and PROVIDER UNAVAILABLE states. Observations retain their source and timestamp. An illustrative calculator is not a ledger or distribution record. Reward records require transaction references and published eligibility rules. Token market data must not be confused with official allocation balances, audited treasury reserves or claimable rewards.'),
('Roadmap', 'The current public platform launch target is Q2 2027; this is a target, not a guarantee. Existing discovery, chart, globe and chat components form the foundation. Contextual intelligence, richer token tools, document delivery and wallet execution are being developed and tested. Fee-Back eligibility infrastructure, audited distribution logic, risk analysis, stronger community moderation and broader execution support require further implementation and validation. Milestones move through PLANNED, BUILDING, TESTING and LIVE based on evidence, not a fixed marketing countdown.'),
('Risk Factors', 'Cryptoassets can lose all value. Markets may be illiquid, manipulated, misleading or inaccessible. Tokens can have mutable authorities, transfer restrictions, malicious code, concentrated ownership or misleading branding. Smart contracts, wallets, APIs, RPC services and the application itself may fail. Price snapshots differ from execution quotes. MEV, slippage, priority fees and confirmation delays can affect outcomes. Any future FEECAT distribution can fluctuate in value after receipt.'),
('Disclosures', 'This document describes product design and approved policy, with functionality subject to verification, provider availability and change. It is not financial, legal or tax advice, a solicitation to buy a token, or a guarantee of rewards. The mint registry is supplied by the project owner and matched against data sources where possible; it is not independently audited. Local watchlists, preferences, missions and alerts are stored in the browser; public chat and relevant application records are stored server-side.'),
('Future Development', 'Future work may include broader market indexing, independently sourced contract risk signals, authenticated moderation, portfolio indexing, additional network execution providers and auditable Fee-Back settlement infrastructure. Any new feature should preserve explicit source lineage and the separation between a hypothesis, a policy, a quote, an executed transaction and a completed distribution. Additional commercial and regulatory requirements may apply.'),
('Conclusion', 'The FEELESS vision is a connected on-chain workspace: $FEE as the heartbeat, the globe as the map, the terminal as the intelligence and trading layer, the Trenches as the conversation, Fee-Back as the intended economic engine and FeeCat as its culture and fee-return delivery layer. Less noise. More alpha. A FeeLess Future. Progress must be real, data must be sourced, and rewards must never be invented.'),
]

def document():
    return {'title': 'FEELESS', 'subtitle': 'Less Noise. More Alpha.', 'tagline': 'A FeeLess Future.',
            'version': '1.0', 'date': '2026-09-19', 'status': 'Product whitepaper · implementation and policy disclosures',
            'launch_target': 'Q2 2027 · target, not a guarantee',
            'contracts': [{'name': name, 'mint': os.environ[f'{name}_MINT'], 'chain': 'Solana'} for name in ['FEE', 'RFEE', 'FEECAT']],
            'chapters': [{'id': f'chapter-{i + 1}', 'number': i + 1, 'title': title, 'text': text} for i, (title, text) in enumerate(CHAPTERS)]}

def render_pdf():
    data = document()
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=52, leftMargin=52, topMargin=70, bottomMargin=55,
                            title='FEELESS — Less Noise. More Alpha.', author='FEELESS')
    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=10, leading=16, textColor=colors.HexColor('#33483d'), spaceAfter=18)
    heading = ParagraphStyle('Heading', fontName='Helvetica-Bold', fontSize=18, leading=24, textColor=colors.HexColor('#073d27'), spaceAfter=13)
    eyebrow = ParagraphStyle('Eyebrow', fontName='Helvetica-Bold', fontSize=8, leading=12, textColor=colors.HexColor('#248c60'), spaceAfter=10)
    cover = ParagraphStyle('Cover', fontName='Helvetica-Bold', fontSize=52, leading=59, textColor=colors.HexColor('#063b26'))
    story = [Spacer(1, 80), Paragraph('FEELESS', cover), Spacer(1, 24), Paragraph('Less Noise. More Alpha.', heading),
             Paragraph('A FeeLess Future.', body), Spacer(1, 45), Paragraph('WHITEPAPER / VERSION 1.0', eyebrow),
             Paragraph('Economic fee-back. Connected intelligence. A community-first on-chain workspace.', body),
             Spacer(1, 30), Paragraph(escape(data['status']), body), Paragraph('Public platform launch target: Q2 2027. Not a guarantee.', body), PageBreak(),
             Paragraph('Contents', heading)]
    for chapter in data['chapters']:
        story.append(Paragraph(f'{chapter["number"]:02d} / {escape(chapter["title"])}', body))
    story += [PageBreak(), Paragraph('Contract registry', heading), Paragraph('Owner-supplied Solana mints. Exact-address matching, not a security endorsement.', body)]
    for contract in data['contracts']:
        story += [Paragraph(contract['name'], eyebrow), Paragraph(contract['mint'], body)]
    story.append(PageBreak())
    for chapter in data['chapters']:
        story.append(KeepTogether([Paragraph(f'{chapter["number"]:02d} / FEELESS', eyebrow),
                                  Paragraph(escape(chapter['title']), heading), Paragraph(escape(chapter['text']), body)]))
        story.append(Spacer(1, 15))
    def page(canvas, document):
        w, h = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#05160d')); canvas.rect(0, h - 43, w, 43, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#00efa0')); canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(52, h - 27, 'FEELESS')
        canvas.setFillColor(colors.HexColor('#d9eee1')); canvas.setFont('Helvetica', 7)
        canvas.drawRightString(w - 52, h - 27, 'LESS NOISE. MORE ALPHA.')
        canvas.setStrokeColor(colors.HexColor('#b5d4bf')); canvas.line(52, 39, w - 52, 39)
        canvas.setFillColor(colors.HexColor('#668974')); canvas.setFont('Helvetica', 7)
        canvas.drawString(52, 26, f'FEELESS / v1.0 / {data["date"]}')
        canvas.drawRightString(w - 52, 26, f'{document.page:02d}')
        logo = Path(__file__).parent.parent / 'frontend/public/assets/feeless-logo.png'
        if document.page == 1 and logo.exists():
            canvas.drawImage(str(logo), w - 142, h - 217, width=75, height=80, mask='auto', preserveAspectRatio=True)
        canvas.restoreState()
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return output.getvalue()

router = APIRouter(prefix='/api/docs')
@router.get('/whitepaper')
async def web_whitepaper():
    return document()

@router.get('/whitepaper.pdf')
def pdf_whitepaper(download: bool = False):
    return Response(render_pdf(), media_type='application/pdf', headers={
        'Content-Disposition': f'{"attachment" if download else "inline"}; filename="FEELESS-Whitepaper-v1.0.pdf"',
        'Cache-Control': 'public, max-age=3600'})