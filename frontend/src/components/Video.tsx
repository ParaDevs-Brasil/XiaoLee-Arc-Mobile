export default class Video {
    private static baseUrl = "xiaolee_hello.mov"; // Começa com um vídeo idle
    private static idleVideo = "xiaolee_standby.mov";
    private static listeners: ((newPfp: string, shouldLoop: boolean) => void)[] = [];
    private static idleTimer: ReturnType<typeof setTimeout> | null = null;
    private static isPlaying: boolean = false; 
    private static isTransitioning: boolean = false;

    private static idleVideos = [
        "xiaolee_standby.mov",
        "xiaolee_standby2.mov",
        "xiaolee_standby3.mov"
    ];

    // Animações expressivas intercaladas no ciclo de idle para manter a
    // personagem viva: pulando, dançando, feliz, surpresa, brava/"não".
    private static expressionVideos = [
        "xiaolee_cheer.mov",
        "xiaolee_kawaii.mov",
        "xiaolee_giggle.mp4",
        "xiaolee_love.mp4",
        "xiaolee_surprise.mov",
        "xiaolee_uncomfortable.mov"
    ];

    // Probabilidade de tocar uma expressão em vez de outro standby a cada troca
    private static EXPRESSION_CHANCE = 0.45;
    
    static setPfp(pfp: string) {
        // Se um vídeo de animação (não idle) estiver tocando, bloqueia a troca.
        if (this.isPlaying) {
            console.log(`Vídeo bloqueado: ${pfp}. Animação principal está tocando.`);
            return; 
        }

        // Limpa o timer de troca de idle anterior para evitar trocas indesejadas
        if (this.idleTimer) {
            clearTimeout(this.idleTimer);
            this.idleTimer = null;
        }

        this.baseUrl = pfp;
        const shouldLoop = this.isIdleVideo(pfp);
        
        // Apenas animações (não-idle) bloqueiam o sistema.
        // Vídeos de Idle podem ser interrompidos a qualquer momento.
        this.isPlaying = !shouldLoop;
      
        this.listeners.forEach(listener => listener(pfp, shouldLoop));
        
        // Se o vídeo for de idle, ele deve entrar no ciclo de troca automática.
        if (shouldLoop) {
            this.scheduleIdleChange();
        }
    }

    // Chamado quando um vídeo de animação (não idle) termina
    static primaryVideoDidEnd() {
        //console.log(`Animação ${this.baseUrl} terminou. Iniciando ciclo de idle.`);
        this.isPlaying = false;
        // Inicia o ciclo de idle com um vídeo aleatório.
        const randomIdle = this.getRandomIdleVideo();
        this.setPfp(randomIdle);
    }

    // Seleciona uma animação expressiva aleatória
    private static getRandomExpressionVideo(): string {
        const randomIndex = Math.floor(Math.random() * this.expressionVideos.length);
        return this.expressionVideos[randomIndex];
    }

    // Seleciona um vídeo idle aleatório
    private static getRandomIdleVideo(): string {
        const randomIndex = Math.floor(Math.random() * this.idleVideos.length);
        //console.log(`Selecionando vídeo idle aleatório: ${this.idleVideos[randomIndex]}`);
        return this.idleVideos[randomIndex];
    }    // Verifica se o vídeo é um vídeo idle
    private static isIdleVideo(pfp: string): boolean {
        return this.idleVideos.includes(pfp);
    }

    // Agenda a troca APENAS entre vídeos de idle que estão em loop
    private static scheduleIdleChange() {
        // Clear any existing timer
        if (this.idleTimer) {
            clearTimeout(this.idleTimer);
        }

        // Schedule next change between 8-15 seconds
        const randomDelay = 8000 + Math.random() * 7000;
        
        this.idleTimer = setTimeout(() => {
            // Only change if still in idle video and not transitioning
            if (this.isIdleVideo(this.baseUrl) && !this.isTransitioning && !this.isPlaying) {
                // Às vezes toca uma expressão (toca uma vez e volta ao idle
                // via primaryVideoDidEnd); senão, troca de standby.
                if (Math.random() < this.EXPRESSION_CHANCE) {
                    this.setPfp(this.getRandomExpressionVideo());
                    return;
                }

                const currentIdle = this.baseUrl;
                let newIdle = this.getRandomIdleVideo();

                // Ensure we don't repeat the same video
                while (newIdle === currentIdle && this.idleVideos.length > 1) {
                    newIdle = this.getRandomIdleVideo();
                }

                this.setPfp(newIdle);
            }
        }, randomDelay);
    }


       static getPfp() {
        return "" + this.baseUrl;
    }

    static setIdleVideo(pfp: string) {
        this.idleVideo = pfp;
    }

    // Verifica se um vídeo está tocando
    static getIsPlaying() {
        return this.isPlaying;
    }

    // Força liberação do estado de playing (usar com cuidado)
    static forceRelease() {
        this.isPlaying = false;
        this.isTransitioning = false;
    }

    // Para o sistema de troca automática
    static stopIdleRotation() {
        if (this.idleTimer) {
            clearTimeout(this.idleTimer);
            this.idleTimer = null;
           
        }
         this.isTransitioning = false;
    }    // Toca um vídeo idle aleatório (útil para chamadas manuais)
    static playRandomIdle() {
        // Verifica se um vídeo está tocando antes de tocar novo
        if (this.isPlaying) {
            //console.log("Bloqueado: Um vídeo já está tocando");
            return;
        }

        const randomIdle = this.getRandomIdleVideo();
        this.setPfp(randomIdle);
    }
    // Sistema de observadores para reatividade
    static subscribe(listener: (newPfp: string, shouldLoop: boolean) => void) {
        this.listeners.push(listener);
        // Retorna função de cleanup
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }
} 