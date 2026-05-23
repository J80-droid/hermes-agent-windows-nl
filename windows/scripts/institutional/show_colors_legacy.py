import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

def main():
    console = Console()
    
    palettes = [
        {
            "name": "1. Monokai Pure (Klassieke Sublime Text 1:1)",
            "colors": {
                "h1": "bold #66d9ef underline",
                "h2": "bold #a6e22e",
                "h3": "bold #e6db74",
                "h4": "bold #ae81ff italic",
                "strong": "bold #fd971f",
                "label": "bold #f92672",
                "text": "#f8f8f2"
            }
        },
        {
            "name": "2. Retro Dracula (Geraffineerde Pastel-look)",
            "colors": {
                "h1": "bold #8be9fd underline",
                "h2": "bold #50fa7b",
                "h3": "bold #ffb86c",
                "h4": "bold #bd93f9 italic",
                "strong": "bold #ff79c6",
                "label": "bold #f92672",
                "text": "#f8f8f2"
            }
        },
        {
            "name": "3. Tokyo Night / Cyberpunk Neon (Giga-Contrast)",
            "colors": {
                "h1": "bold #00f0ff underline",
                "h2": "bold #39ff14",
                "h3": "bold #fff000",
                "h4": "bold #b10dc9 italic",
                "strong": "bold #ff5e00",
                "label": "bold #ff007f",
                "text": "#e0f7fa"
            }
        },
        {
            "name": "4. Nordic Frost / Slate Accent (Scandinavische rust met Hot Pink)",
            "colors": {
                "h1": "bold #88c0d0 underline",
                "h2": "bold #8fbcbb",
                "h3": "bold #81a1c1",
                "h4": "bold #b48ead italic",
                "strong": "bold #d08770",
                "label": "bold #f92672",
                "text": "#eceff4"
            }
        },
        {
            "name": "5. Pacific Deep (Diepzee Cyaan & Teal)",
            "colors": {
                "h1": "bold #20b2aa underline",
                "h2": "bold #98fb98",
                "h3": "bold #afeeee",
                "h4": "bold #dda0dd italic",
                "strong": "bold #ff7f50",
                "label": "bold #f92672",
                "text": "#e0eee0"
            }
        }
    ]

    console.print(Panel("[bold #f92672]HERMES KLEURENPALET VISUALISATIE[/]", border_style="#f92672"))
    console.print("Hieronder ziet u hoe de koppen, labels en tekstblokken er daadwerkelijk uitzien in uw terminal.\n")

    for p in palettes:
        p_name = p["name"]
        c = p["colors"]
        
        # Build the preview text
        preview = Text()
        preview.append("\n# PARTE I: MARCO JURÍDICO Y DE POLÍTICAS\n", style=c["h1"])
        preview.append("## BLOQUES DE EXPEDIENTE COMPARATIVOS\n", style=c["h2"])
        preview.append("### 1. LA PASANTÍA DE 6 SEMANAS COMO TRAMPA PROCESAL DE BZ\n\n", style=c["h3"])
        
        preview.append("Riesgo oculto:\n", style=c["label"])
        preview.append("El Ministerio de Asuntos Exteriores busca crear de manera premeditada un expediente de \"falta de idoneidad\" (ongeschiktheid). Al negarse a definir criterios ", style=c["text"])
        preview.append("SMART objetivos", style=c["strong"])
        preview.append(", cualquier valoración subjetiva de los mandos de BBV en La Haya será utilizada en su contra para justificar un despido bajo la ley WNRA.\n\n", style=c["text"])
        
        preview.append("Alternativa táctica superior:\n", style=c["label"])
        preview.append("Rechazar formalmente por escrito la naturaleza \"evaluativa\" de la pasantía.\n", style=c["text"])

        panel = Panel(preview, title=f"[bold #f8f8f2]{p_name}[/]", border_style=c["h1"].split()[-1].replace("underline", "").strip(), padding=(1, 2))
        console.print(panel)
        console.print()

if __name__ == "__main__":
    main()
