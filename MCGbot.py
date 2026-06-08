import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime
import os
from threading import Thread
from flask import Flask

# ==========================================
# SERVEUR WEB FANTÔME POUR RENDER (ANTI-TIMEOUT)
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "Bot en ligne !"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Lance le mini-serveur en arrière-plan
Thread(target=run_web).start()

# ==========================================
# CONFIGURATION INITIALE ET INTENTS
# ==========================================

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True

class GoalsBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.quotes = []
        self.matchs = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("⚡ [Système] Toutes les commandes slash ont été synchronisées avec Discord.")

bot = GoalsBot()

@bot.event
async def on_ready():
    print("==================================================")
    print(f"🤖 Bot connecté avec succès !")
    print(f"👑 Nom du bot : {bot.user.name}")
    print(f"🆔 ID du bot : {bot.user.id}")
    print("==================================================")
    await bot.change_presence(activity=discord.Game(name="Goals eSports ⚽ | /help"))

# ==========================================
# INTERFACES INTÉGRÉES (BOUTONS & MENUS)
# ==========================================

class MatchButtons(discord.ui.View):
    def __init__(self, match_id, bot_instance):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.bot = bot_instance

    @discord.ui.button(label="✅ Présent", style=discord.ButtonStyle.green, custom_id="match_present")
    async def present_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        match = self.bot.matchs.get(self.match_id)
        if not match:
            await interaction.response.send_message("❌ Ce match n'existe plus.", ephemeral=True)
            return
        
        user_mention = interaction.user.mention
        if user_mention in match["absents"]: match["absents"].remove(user_mention)
        if user_mention in match["retards"]: match["retards"].remove(user_mention)
        
        if user_mention not in match["presents"]:
            match["presents"].append(user_mention)
            await self.update_match_embed(interaction)
        else:
            await interaction.response.send_message("Tu es déjà inscrit comme présent !", ephemeral=True)

    @discord.ui.button(label="⏳ En retard", style=discord.ButtonStyle.blurple, custom_id="match_late")
    async def late_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        match = self.bot.matchs.get(self.match_id)
        if not match:
            await interaction.response.send_message("❌ Ce match n'existe plus.", ephemeral=True)
            return
        
        user_mention = interaction.user.mention
        if user_mention in match["presents"]: match["presents"].remove(user_mention)
        if user_mention in match["absents"]: match["absents"].remove(user_mention)
        
        if user_mention not in match["retards"]:
            match["retards"].append(user_mention)
            await self.update_match_embed(interaction)
        else:
            await interaction.response.send_message("Tu es déjà inscrit comme en retard !", ephemeral=True)

    @discord.ui.button(label="❌ Absent", style=discord.ButtonStyle.red, custom_id="match_absent")
    async def absent_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        match = self.bot.matchs.get(self.match_id)
        if not match:
            await interaction.response.send_message("❌ Ce match n'existe plus.", ephemeral=True)
            return
        
        user_mention = interaction.user.mention
        if user_mention in match["presents"]: match["presents"].remove(user_mention)
        if user_mention in match["retards"]: match["retards"].remove(user_mention)
        
        if user_mention not in match["absents"]:
            match["absents"].append(user_mention)
            await self.update_match_embed(interaction)
        else:
            await interaction.response.send_message("Tu es déjà inscrit comme absent !", ephemeral=True)

    async def update_match_embed(self, interaction: discord.Interaction):
        match = self.bot.matchs.get(self.match_id)
        embed = interaction.message.embeds[0]
        
        embed.set_field_at(0, name=f"✅ Présents ({len(match['presents'])})", value=", ".join(match["presents"]) if match["presents"] else "Aucun", inline=False)
        embed.set_field_at(1, name=f"⏳ En retard ({len(match['retards'])})", value=", ".join(match["retards"]) if match["retards"] else "Aucun", inline=False)
        embed.set_field_at(2, name=f"❌ Absents ({len(match['absents'])})", value=", ".join(match["absents"]) if match["absents"] else "Aucun", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)


class RoleButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚽ Joueur Goals", style=discord.ButtonStyle.primary, emoji="⚽", custom_id="role_goals")
    async def goals_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="⚽ | Joueur Goals")
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Rôle `Joueur Goals` retiré !", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Rôle `Joueur Goals` ajouté !", ephemeral=True)

    @discord.ui.button(label="🎮 Membre Casual", style=discord.ButtonStyle.secondary, emoji="🎮", custom_id="role_casual")
    async def casual_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="🎮 | Membre Casual")
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Rôle `Membre Casual` retiré !", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Rôle `Membre Casual` ajouté !", ephemeral=True)


# ==========================================
# COMMANDES ADMINISTRATION & CONFIGURATION
# ==========================================

@bot.tree.command(name="serveur-create", description="[ADMIN] Configure de zéro l'intégralité du serveur pour Goals")
@app_commands.checks.has_permissions(administrator=True)
async def serveur_create(interaction: discord.Interaction):
    await interaction.response.send_message("🏗️ Configuration globale lancée. Nettoyage et création en cours...", ephemeral=True)
    guild = interaction.guild

    for channel in guild.channels:
        try:
            await channel.delete()
        except Exception:
            pass

    role_staff = await guild.create_role(name="👑 | Staff", color=discord.Color.from_rgb(231, 76, 60), mentionable=True, hoist=True)
    role_joueur = await guild.create_role(name="⚽ | Joueur Goals", color=discord.Color.from_rgb(52, 152, 219), mentionable=True, hoist=True)
    role_casual = await guild.create_role(name="🎮 | Membre Casual", color=discord.Color.from_rgb(149, 165, 166), mentionable=True, hoist=True)

    perms_prive = discord.PermissionOverwrite(view_channel=False)
    perms_staff = discord.PermissionOverwrite(manage_channels=True, manage_messages=True, mute_members=True, view_channel=True)

    cat_welcome = await guild.create_category("📌 ‖ ACCUEIL")
    chan_regles = await guild.create_text_channel("📜・règlement", category=cat_welcome)
    await guild.create_text_channel("📢・annonces", category=cat_welcome)
    chan_roles = await guild.create_text_channel("🎭・choix-roles", category=cat_welcome)

    cat_goals = await guild.create_category("⚽ ‖ CLUB GOALS")
    await guild.create_text_channel("💬・général", category=cat_goals)
    await guild.create_text_channel("📅・matchs-et-scrimes", category=cat_goals)
    await guild.create_text_channel("📊・stats-et-clips", category=cat_goals)
    await guild.create_text_channel("💬・quotes-cultes", category=cat_goals)
    
    await guild.create_voice_channel("🔊｜Général Vocal", category=cat_goals)
    await guild.create_voice_channel("🎮｜Squad Alpha (Match)", category=cat_goals, user_limit=5)
    await guild.create_voice_channel("🎮｜Squad Beta (Match)", category=cat_goals, user_limit=5)

    cat_staff = await guild.create_category("🔒 ‖ STAFF ONLY")
    overwrites_staff = {guild.default_role: perms_prive, role_staff: perms_staff}
    await guild.create_text_channel("🤫・bureau-staff", category=cat_staff, overwrites=overwrites_staff)
    await guild.create_voice_channel("🤫・Réunion Staff", category=cat_staff, overwrites=overwrites_staff)

    await chan_regles.send(
        "Welcome dans l'équipe ! ⚽\n"
        "1. Respect mutuel (on joue pour le fun !)\n"
        "2. Pas de toxicité en match ou en vocal.\n"
        "3. Indique tes disponibilités dans le salon dédié."
    )

    embed_role = discord.Embed(
        title="🎭 Attribution des Rôles", 
        description="Clique sur les boutons ci-dessous pour t'attribuer ou te retirer un rôle sur le serveur.",
        color=discord.Color.green()
    )
    await chan_roles.send(embed=embed_role, view=RoleButtons())

    try:
        await interaction.user.send("✅ Le serveur a été configuré avec succès ! Les rôles Staff, Joueur Goals et Membre Casual sont prêts.")
    except discord.Forbidden:
        pass


@bot.tree.command(name="setup-roles", description="[ADMIN] Renvoie le panneau des boutons de rôles.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_roles(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎭 Rejoins l'équipe !", 
        description="Choisis tes rôles pour être notifié des matchs ou simplement discuter.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message("Panneau envoyé !", ephemeral=True)
    await interaction.channel.send(embed=embed, view=RoleButtons())


# ==========================================
# SYSTEME DE MATCHS ET PLANNING
# ==========================================

@bot.tree.command(name="match-creer", description="Planifie un match ou un entraînement Goals")
@app_commands.describe(titre="Nom de l'événement (ex: Scrim face aux Voisins)", date="Date et heure (ex: Dimanche 21h)")
async def match_creer(interaction: discord.Interaction, titre: str, date: str):
    match_id = str(random.randint(1000, 9999))
    
    bot.matchs[match_id] = {
        "titre": titre,
        "date": date,
        "presents": [],
        "retards": [],
        "absents": []
    }

    embed = discord.Embed(
        title=f"⚽ MATCH PLANIFIÉ : {titre}",
        description=f"📅 **Date & Heure :** {date}\n🆔 **ID Match :** {match_id}\n\nMerci de réagir avec les boutons ci-dessous pour confirmer votre présence !",
        color=discord.Color.gold()
    )
    embed.add_field(name="✅ Présents (0)", value="Aucun", inline=False)
    embed.add_field(name="⏳ En retard (0)", value="Aucun", inline=False)
    embed.add_field(name="❌ Absents (0)", value="Aucun", inline=False)
    embed.set_footer(text="Système de gestion eSports Goals")

    await interaction.response.send_message(f"Match {match_id} créé !", ephemeral=True)
    await interaction.channel.send(embed=embed, view=MatchButtons(match_id, bot))


@bot.tree.command(name="match-ping", description="Ping tous les joueurs inscrits au match pour leur rappeler l'heure")
@app_commands.describe(match_id="L'ID du match à relancer")
async def match_ping(interaction: discord.Interaction, match_id: str):
    match = bot.matchs.get(match_id)
    if not match:
        await interaction.response.send_message("❌ ID de match introuvable.", ephemeral=True)
        return

    if not match["presents"] and not match["retards"]:
        await interaction.response.send_message("Personne n'est inscrit à ce match pour le moment.", ephemeral=True)
        return

    destinataires = match["presents"] + match["retards"]
    liste_ping = " ".join(destinataires)
    
    await interaction.response.send_message("Rappel envoyé !", ephemeral=True)
    await interaction.channel.send(f"🔔 **Rappel de Match ({match['titre']}) !**\nOn se prépare les gars : {liste_ping} ! Le coup d'envoi approche ({match['date']}).")


# ==========================================
# FONCTIONNALITÉ STREAM / CAST
# ==========================================

@bot.tree.command(name="cast", description="Annonce publiquement que tu lances le cast / stream du match")
@app_commands.describe(lien_twitch="Le lien complet de ta chaîne Twitch (ex: https://twitch.tv/ton_pseudo)")
async def cast(interaction: discord.Interaction, lien_twitch: str):
    if "twitch.tv" not in lien_twitch.lower():
        await interaction.response.send_message("❌ Cela ne ressemble pas à un lien Twitch valide. Réessaie !", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎥 MATCH EN STREAM !",
        description=f"📢 {interaction.user.mention} est en train de streamer le match de l'équipe !\n\nVenez tous donner de la force sur le chat et regarder le spectacle !",
        color=discord.Color.from_rgb(145, 70, 255)
    )
    embed.add_field(name="🎮 Chaîne à rejoindre", value=f"[Clique ici pour regarder le live]({lien_twitch})", inline=False)
    embed.set_thumbnail(url="https://pngimg.com/uploads/twitch/twitch_PNG28.png")
    embed.set_footer(text=f"Lancé par {interaction.user.display_name}")

    await interaction.response.send_message("Annonce de stream envoyée !", ephemeral=True)
    await interaction.channel.send(content="🔔 @everyone **Le match est diffusé en direct !**", embed=embed)


# ==========================================
# FONCTIONNALITÉS FUN & COMMUNAUTÉ
# ==========================================

@bot.tree.command(name="random-team", description="Sépare équitablement les joueurs du vocal dans deux équipes aléatoires")
async def random_team(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ Tu dois être connecté dans un salon vocal pour utiliser cette commande.", ephemeral=True)
        return

    membres = interaction.user.voice.channel.members
    if len(membres) < 2:
        await interaction.response.send_message("❌ Il faut au moins 2 joueurs dans le salon vocal pour composer des équipes.", ephemeral=True)
        return

    noms_joueurs = [m.mention for m in membres]
    random.shuffle(noms_joueurs)

    milieu = len(noms_joueurs) // 2
    equipe_bleue = noms_joueurs[:milieu]
    equipe_rouge = noms_joueurs[milieu:]

    embed = discord.Embed(
        title="⚽ COMPOSITION DES ÉQUIPES ALÉATOIRES",
        description="Le destin a parlé, voici la répartition pour la prochaine partie !",
        color=discord.Color.purple()
    )
    embed.add_field(name="🔵 Équipe Bleue", value="\n".join(equipe_bleue), inline=True)
    embed.add_field(name="🔴 Équipe Rouge", value="\n".join(equipe_rouge), inline=True)
    embed.set_footer(text="Que le meilleur gagne (pas de jaloux !)")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="quote-add", description="Enregistre une punchline ou une phrase culte dite sur le vocal")
@app_commands.describe(auteur="Le joueur qui a dit la phrase", phrase="La phrase légendaire")
async def quote_add(interaction: discord.Interaction, auteur: discord.Member, phrase: str):
    date_jour = datetime.date.today().strftime("%d/%m/%Y")
    nouvelle_quote = {
        "auteur": auteur.display_name,
        "phrase": phrase,
        "par": interaction.user.display_name,
        "date": date_jour
    }
    bot.quotes.append(nouvelle_quote)
    
    embed = discord.Embed(
        title="🎙️ Nouvelle Citation Enregistrée !",
        description=f'« *{phrase}* »',
        color=discord.Color.dark_gold()
    )
    embed.add_field(name="👤 Parole de", value=auteur.mention, inline=True)
    embed.add_field(name="✍️ Noté par", value=interaction.user.mention, inline=True)
    embed.set_footer(text=f"Gravé dans l'histoire le {date_jour}")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="quote-random", description="Affiche une phrase culte au hasard issue de votre historique")
async def quote_random(interaction: discord.Interaction):
    if not bot.quotes:
        citations_defaut = [
            {"auteur": "Le Coach", "phrase": "Lâche ton sprint, tu vas griller toute ton endurance !", "par": "Système", "date": "01/01/2026"},
            {"auteur": "L'attaquant", "phrase": "Mais j'ai appuyé sur la touche de tir !!! C'est scripté !", "par": "Système", "date": "15/02/2026"},
            {"auteur": "Le Goal", "phrase": "Ne vous inquiétez pas je gère le cageot... Ah, but.", "par": "Système", "date": "10/04/2026"}
        ]
        q = random.choice(citations_defaut)
    else:
        q = random.choice(bot.quotes)

    embed = discord.Embed(
        title="📜 Archives Légendaires du Club",
        description=f'« **{q["phrase"]}** »',
        color=discord.Color.teal()
    )
    embed.add_field(name="🗣️ Auteur", value=q["auteur"], inline=True)
    embed.add_field(name="📅 Date", value=q["date"], inline=True)
    embed.set_footer(text=f"Rapporté par {q['par']}")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="mvp-vote", description="Lance un vote pour élire le joueur le plus fort ou le plus drôle de la session")
@app_commands.describe(nom_un="Joueur en lice numéro 1", nom_deux="Joueur en lice numéro 2")
async def mvp_vote(interaction: discord.Interaction, nom_un: discord.Member, nom_deux: discord.Member):
    embed = discord.Embed(
        title="🏆 ÉLECTION DU MVP DU SOIR",
        description="La session de jeu Goals se termine ! Qui mérite le titre honorifique de MVP aujourd'hui ? Votez avec les réactions !",
        color=discord.Color.orange()
    )
    embed.add_field(name="1️⃣ Candidat Alpha", value=nom_un.mention, inline=True)
    embed.add_field(name="2️⃣ Candidat Beta", value=nom_deux.mention, inline=True)
    embed.set_footer(text="Fin des votes quand le staff le décide !")

    await interaction.response.send_message("Le vote pour le MVP est lancé !", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    
    await message.add_reaction("1️⃣")
    await message.add_reaction("2️⃣")


# ==========================================
# UTILITAIRES ET COMMANDES D'AIDE
# ==========================================

@bot.tree.command(name="help", description="Affiche la liste complète des fonctionnalités disponibles sur le bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Manuel d'Utilisation du Bot Goals",
        description="Voici la liste triée de tout ce que je peux faire pour animer votre structure fun !",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🏗️ Administration", 
        value="`/serveur-create` : Crée les catégories, salons configurés et boutons.\n"
              "`/setup-roles` : Renvoie le panneau d'attribution des rôles.", 
        inline=False
    )
    
    embed.add_field(
        name="📅 Gestion Matchs & Compétitions", 
        value="`/match-creer [titre] [date]` : Planifie un match avec un système interactif de présence.\n"
              "`/match-ping [id_match]` : Alerte instantanément les inscrits d'une session imminente.\n"
              "`/cast [lien_twitch]` : Annonce en grand avec une alerte que tu streams le match !", 
        inline=False
    )
    
    embed.add_field(
        name="🎉 Cohésion & Animation Fun", 
        value="`/random-team` : Répartit automatiquement en 2 groupes distincts les gens en vocal.\n"
              "`/quote-add [joueur] [phrase]` : Enregistre une bêtise ou une phrase folle.\n"
              "`/quote-random` : Pioche au hasard une citation mythique de l'équipe.\n"
              "`/mvp-vote [joueur1] [joueur2]` : Crée un sondage pour le meilleur joueur de la soirée.", 
        inline=False
    )
    
    embed.set_footer(text="Développé spécialement pour votre team casual.")
    await interaction.response.send_message(embed=embed)


# ==========================================
# EVENEMENTS AVANCÉS (BIENVENUE)
# ==========================================

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="💬・général")
    if channel:
        embed = discord.Embed(
            title="👋 Un nouveau joueur entre sur le terrain !",
            description=f"Bienvenue {member.mention} au sein du club eSports Goals ! Passe au salon des rôles pour t'équiper !",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

# ==========================================
# LANCEMENT DU BOT SECURISE
# ==========================================

bot.run(os.environ.get('DISCORD_TOKEN'))