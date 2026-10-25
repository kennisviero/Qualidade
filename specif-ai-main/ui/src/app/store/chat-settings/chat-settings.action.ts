import { ChatSettings } from "src/app/model/interfaces/ChatSettings";

export class SetChatSettings {
    static readonly type = '[SetChatSettings] Set';
    constructor(public payload: ChatSettings) { }
}