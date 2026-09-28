import { ChevronDownIcon, UserIcon } from "@/components/Icons";

export function UserMenu() {
  return (
    <div className="topbar">
      <button className="user-menu" type="button">
        <UserIcon size={32} />
        Студент
        <ChevronDownIcon size={18} />
      </button>
    </div>
  );
}
